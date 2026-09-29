from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.cf_patch.__main__ import main, patch_tables
from tools.cf_patch.backup import restore_backup
from tools.cf_patch.unity_text import TextAssetDiscoveryError


FIX = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).parent.parent


class FakeTextAsset:
    def __init__(self, name: str, script: str):
        self.m_Name = name
        self.m_Script = script

    def save(self):
        pass


class FakeObject:
    type = SimpleNamespace(name="TextAsset")

    def __init__(self, asset: FakeTextAsset):
        self.asset = asset

    def read(self):
        return self.asset


class FakeEnvironment:
    def __init__(self, assets, before_save=None):
        self.assets = assets
        self.objects = [FakeObject(asset) for asset in assets]
        self.before_save = before_save

    def save(self, pack="none", out_path="output"):
        assert isinstance(out_path, str)
        if self.before_save:
            self.before_save()
        Path(out_path, "resources.assets").write_bytes(b"patched-assets")


def _source_assets():
    return [
        FakeTextAsset(
            "UnitTypeData",
            (FIX / "sample_unittype_snippet.xml").read_text(encoding="utf-8"),
        ),
        FakeTextAsset(
            "CharacterData",
            (FIX / "sample_character_snippet.xml").read_text(encoding="utf-8"),
        ),
        FakeTextAsset(
            "LanguageData",
            (FIX / "sample_language_snippet.xml").read_text(encoding="utf-8"),
        ),
    ]


def _game(tmp_path: Path) -> Path:
    game_root = tmp_path / "game"
    data_dir = game_root / "Chaos Front_Data"
    data_dir.mkdir(parents=True)
    (data_dir / "resources.assets").write_bytes(b"original-assets")
    (data_dir / "resources.assets.resS").write_bytes(b"original-stream")
    return game_root


def test_patch_tables_backs_up_before_save_and_replaces_assets(tmp_path, monkeypatch):
    game_root = _game(tmp_path)
    backups_dir = tmp_path / "backups"

    def assert_backup_exists():
        backups = list(backups_dir.iterdir())
        assert len(backups) == 1
        assert (backups[0] / "resources.assets").read_bytes() == b"original-assets"
        assert (backups[0] / "resources.assets.resS").read_bytes() == b"original-stream"

    env = FakeEnvironment(_source_assets(), before_save=assert_backup_exists)
    monkeypatch.setattr("tools.cf_patch.__main__.UnityPy.load", lambda _: env)

    backup_dir, meta = patch_tables(
        game_root, ROOT / "patches/v1-rx78.yaml", backups_dir
    )

    assert backup_dir.parent == backups_dir
    assert meta["unit_id"] == 93
    assert (game_root / "Chaos Front_Data/resources.assets").read_bytes() == (
        b"patched-assets"
    )
    assert 'Index="93"' in env.assets[0].m_Script
    assert 'Index="1121"' in env.assets[1].m_Script


def test_patch_tables_closes_source_stream_before_replace(tmp_path, monkeypatch):
    game_root = _game(tmp_path)
    env = FakeEnvironment(_source_assets())
    loaded = {}
    real_replace = __import__("os").replace

    def load(source):
        loaded["source"] = source
        return env

    def replace(source, destination):
        assert loaded["source"].closed is True
        real_replace(source, destination)

    monkeypatch.setattr("tools.cf_patch.__main__.UnityPy.load", load)
    monkeypatch.setattr("tools.cf_patch.__main__.os.replace", replace)

    patch_tables(
        game_root, ROOT / "patches/v1-rx78.yaml", tmp_path / "backups"
    )


def test_patch_tables_cleans_staging_directory_when_save_fails(tmp_path, monkeypatch):
    game_root = _game(tmp_path)
    env = FakeEnvironment(_source_assets())

    def fail_save(pack="none", out_path="output"):
        raise OSError("save failed")

    env.save = fail_save
    monkeypatch.setattr("tools.cf_patch.__main__.UnityPy.load", lambda _: env)

    with pytest.raises(OSError, match="save failed"):
        patch_tables(
            game_root, ROOT / "patches/v1-rx78.yaml", tmp_path / "backups"
        )

    data_dir = game_root / "Chaos Front_Data"
    assert not list(data_dir.glob(".cf-patch-*"))
    assert (data_dir / "resources.assets").read_bytes() == b"original-assets"


def test_patch_tables_aborts_before_backup_when_unit_exists(tmp_path, monkeypatch):
    game_root = _game(tmp_path)
    backups_dir = tmp_path / "backups"
    assets = _source_assets()
    assets[0].m_Script = '<UnitTypeData><Item Index="93"/></UnitTypeData>'
    monkeypatch.setattr(
        "tools.cf_patch.__main__.UnityPy.load", lambda _: FakeEnvironment(assets)
    )

    with pytest.raises(RuntimeError, match="Index 93"):
        patch_tables(game_root, ROOT / "patches/v1-rx78.yaml", backups_dir)

    assert not backups_dir.exists()
    assert (game_root / "Chaos Front_Data/resources.assets").read_bytes() == (
        b"original-assets"
    )


def test_patch_tables_always_aborts_when_unit_93_exists(tmp_path, monkeypatch):
    game_root = _game(tmp_path)
    backups_dir = tmp_path / "backups"
    patch_path = tmp_path / "unit-94.yaml"
    patch_path.write_text(
        (ROOT / "patches/v1-rx78.yaml")
        .read_text(encoding="utf-8")
        .replace("  id: 93", "  id: 94", 1),
        encoding="utf-8",
    )
    assets = _source_assets()
    assets[0].m_Script = '<UnitTypeData><Item Index="93"/></UnitTypeData>'
    monkeypatch.setattr(
        "tools.cf_patch.__main__.UnityPy.load", lambda _: FakeEnvironment(assets)
    )

    with pytest.raises(RuntimeError, match="Index 93"):
        patch_tables(game_root, patch_path, backups_dir)

    assert not backups_dir.exists()
    assert (game_root / "Chaos Front_Data/resources.assets").read_bytes() == (
        b"original-assets"
    )


def test_patch_tables_aborts_before_backup_when_character_exists(tmp_path, monkeypatch):
    game_root = _game(tmp_path)
    backups_dir = tmp_path / "backups"
    assets = _source_assets()
    assets[1].m_Script = '<CharacterData><Item Index="1121"/></CharacterData>'
    monkeypatch.setattr(
        "tools.cf_patch.__main__.UnityPy.load", lambda _: FakeEnvironment(assets)
    )

    with pytest.raises(RuntimeError, match="CharacterData Index 1121"):
        patch_tables(game_root, ROOT / "patches/v1-rx78.yaml", backups_dir)

    assert not backups_dir.exists()
    assert (game_root / "Chaos Front_Data/resources.assets").read_bytes() == (
        b"original-assets"
    )


def test_patch_tables_always_aborts_when_character_1121_exists(tmp_path, monkeypatch):
    game_root = _game(tmp_path)
    backups_dir = tmp_path / "backups"
    patch_path = tmp_path / "character-1122.yaml"
    patch_path.write_text(
        (ROOT / "patches/v1-rx78.yaml")
        .read_text(encoding="utf-8")
        .replace("  id: 1121", "  id: 1122", 1),
        encoding="utf-8",
    )
    assets = _source_assets()
    assets[1].m_Script = '<CharacterData><Item Index="1121"/></CharacterData>'
    monkeypatch.setattr(
        "tools.cf_patch.__main__.UnityPy.load", lambda _: FakeEnvironment(assets)
    )

    with pytest.raises(RuntimeError, match="CharacterData Index 1121"):
        patch_tables(game_root, patch_path, backups_dir)

    assert not backups_dir.exists()


def test_patch_tables_reports_inventory_before_backup_on_missing_asset(
    tmp_path, monkeypatch
):
    game_root = _game(tmp_path)
    backups_dir = tmp_path / "backups"
    assets = _source_assets()[:2]
    monkeypatch.setattr(
        "tools.cf_patch.__main__.UnityPy.load", lambda _: FakeEnvironment(assets)
    )

    with pytest.raises(TextAssetDiscoveryError, match="UnitTypeData"):
        patch_tables(game_root, ROOT / "patches/v1-rx78.yaml", backups_dir)

    assert not backups_dir.exists()


def test_texture_injection_runs_after_backup_and_preserves_original_on_abort(
    tmp_path, monkeypatch
):
    game_root = _game(tmp_path)
    backups_dir = tmp_path / "backups"
    env = FakeEnvironment(_source_assets())

    def abort_texture_injection(env_arg, manifest, assets_root):
        assert env_arg is env
        backups = list(backups_dir.iterdir())
        assert len(backups) == 1
        assert (backups[0] / "resources.assets").read_bytes() == b"original-assets"
        raise RuntimeError("cannot safely clone textures")

    monkeypatch.setattr("tools.cf_patch.__main__.UnityPy.load", lambda _: env)
    monkeypatch.setattr(
        "tools.cf_patch.__main__.inject_textures", abort_texture_injection
    )

    with pytest.raises(RuntimeError, match="cannot safely clone"):
        patch_tables(
            game_root,
            ROOT / "patches/v1-rx78.yaml",
            backups_dir,
            inject_texture_assets=True,
        )

    assert (game_root / "Chaos Front_Data/resources.assets").read_bytes() == (
        b"original-assets"
    )
    assert (game_root / "Chaos Front_Data/resources.assets.resS").read_bytes() == (
        b"original-stream"
    )


def test_main_restore_restores_default_resource_files(tmp_path):
    game_root = _game(tmp_path)
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    (backup_dir / "resources.assets").write_bytes(b"backup-assets")
    (backup_dir / "resources.assets.resS").write_bytes(b"backup-stream")

    exit_code = main(["--restore", str(backup_dir), "--game", str(game_root)])

    assert exit_code == 0
    assert (game_root / "Chaos Front_Data/resources.assets").read_bytes() == (
        b"backup-assets"
    )
    assert (game_root / "Chaos Front_Data/resources.assets.resS").read_bytes() == (
        b"backup-stream"
    )


def test_restore_backup_stages_each_file_before_replace(tmp_path, monkeypatch):
    game_root = _game(tmp_path)
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    (backup_dir / "resources.assets").write_bytes(b"backup-assets")
    (backup_dir / "resources.assets.resS").write_bytes(b"backup-stream")
    replacements = []
    real_replace = __import__("os").replace

    def replace(source, destination):
        source = Path(source)
        destination = Path(destination)
        assert source.parent == destination.parent
        assert source != destination
        replacements.append((source.name, destination.name))
        real_replace(source, destination)

    monkeypatch.setattr("tools.cf_patch.backup.os.replace", replace)

    restore_backup(backup_dir, game_root)

    assert [destination for _, destination in replacements] == [
        "resources.assets",
        "resources.assets.resS",
    ]
    assert (game_root / "Chaos Front_Data/resources.assets").read_bytes() == (
        b"backup-assets"
    )
    assert (game_root / "Chaos Front_Data/resources.assets.resS").read_bytes() == (
        b"backup-stream"
    )


@pytest.mark.parametrize(
    ("extra_args", "expected"),
    [([], True), (["--tables-only"], False)],
)
def test_main_wires_texture_injection_unless_tables_only(
    tmp_path, monkeypatch, extra_args, expected
):
    captured = {}

    def fake_patch_tables(
        game_root,
        patch_path,
        backups_dir,
        *,
        inject_texture_assets=False,
    ):
        captured["inject_texture_assets"] = inject_texture_assets
        return tmp_path / "backup", {"unit_id": 93, "character_id": 1121}

    monkeypatch.setattr("tools.cf_patch.__main__.patch_tables", fake_patch_tables)

    exit_code = main(
        [
            "--game",
            str(tmp_path / "game"),
            "--patch",
            str(tmp_path / "patch.yaml"),
            *extra_args,
        ]
    )

    assert exit_code == 0
    assert captured["inject_texture_assets"] is expected


def test_patch_tables_writes_patch_meta_into_backup_directory(tmp_path, monkeypatch):
    game_root = _game(tmp_path)
    env = FakeEnvironment(_source_assets())
    monkeypatch.setattr("tools.cf_patch.__main__.UnityPy.load", lambda _: env)

    backup_dir, meta = patch_tables(
        game_root, ROOT / "patches/v1-rx78.yaml", tmp_path / "backups"
    )

    assert (backup_dir / "patch-meta.json").read_text(encoding="utf-8") == (
        __import__("json").dumps(meta, ensure_ascii=False, indent=2) + "\n"
    )
