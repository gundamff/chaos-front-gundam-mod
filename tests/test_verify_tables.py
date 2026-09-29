from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.cf_patch.unity_text import TextAssetDiscoveryError
from tools.verify_tables import verify, verify_baseline, verify_patched

FIX = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).parent.parent


class FakeTextAsset:
    def __init__(self, name: str, script: str):
        self.m_Name = name
        self.m_Script = script


class FakeObject:
    type = SimpleNamespace(name="TextAsset")

    def __init__(self, asset: FakeTextAsset):
        self.asset = asset

    def read(self):
        return self.asset


class FakeEnvironment:
    def __init__(self, assets):
        self.objects = [FakeObject(asset) for asset in assets]


def _baseline_tables():
    return {
        "UnitTypeData": (FIX / "sample_unittype_snippet.xml").read_text(encoding="utf-8"),
        "CharacterData": (FIX / "sample_character_snippet.xml").read_text(encoding="utf-8"),
        "LanguageData": (FIX / "sample_language_snippet.xml").read_text(encoding="utf-8"),
    }


def _patched_tables():
    from tools.cf_patch.table_patch import apply_v1_tables
    import yaml

    patch = yaml.safe_load((ROOT / "patches/v1-rx78.yaml").read_text(encoding="utf-8"))
    u, c, l, _ = apply_v1_tables(
        _baseline_tables()["UnitTypeData"],
        _baseline_tables()["CharacterData"],
        _baseline_tables()["LanguageData"],
        patch,
    )
    return {"UnitTypeData": u, "CharacterData": c, "LanguageData": l}


def test_verify_baseline_passes_on_snippet():
    assert verify_baseline(_baseline_tables()) == []


def test_verify_baseline_fails_when_unit_93_present():
    tables = _patched_tables()
    errors = verify_baseline(tables)
    assert any("UnitTypeData Index 93" in err for err in errors)


def test_verify_patched_passes_with_patch_yaml():
    errors = verify_patched(
        _patched_tables(),
        meta_path=None,
        patch_path=ROOT / "patches/v1-rx78.yaml",
        require_full_count=False,
    )
    assert errors == []


def test_verify_patched_uses_meta_language_indices(tmp_path):
    tables = _patched_tables()
    meta_path = tmp_path / "patch-meta.json"
    meta_path.write_text(
        '{"language_indices":{"unit_name":999,"unit_info":4,"char_name":5,"char_info":6}}',
        encoding="utf-8",
    )
    errors = verify_patched(
        tables,
        meta_path=meta_path,
        patch_path=ROOT / "patches/v1-rx78.yaml",
        require_full_count=False,
    )
    assert any("LanguageData Index=999" in err for err in errors)


def test_verify_integration_with_fake_assets(tmp_path, monkeypatch):
    game_root = tmp_path / "game"
    data_dir = game_root / "Chaos Front_Data"
    data_dir.mkdir(parents=True)
    (data_dir / "resources.assets").write_bytes(b"fake")

    tables = _patched_tables()
    env = FakeEnvironment(
        [
            FakeTextAsset("UnitTypeData", tables["UnitTypeData"]),
            FakeTextAsset("CharacterData", tables["CharacterData"]),
            FakeTextAsset("LanguageData", tables["LanguageData"]),
        ]
    )
    monkeypatch.setattr("tools.verify_tables.UnityPy.load", lambda _: env)

    errors = verify(
        data_dir / "resources.assets",
        baseline=False,
        meta_path=None,
        patch_path=ROOT / "patches/v1-rx78.yaml",
        require_full_count=False,
    )
    assert errors == []


def test_verify_reports_missing_assets(tmp_path):
    game_root = tmp_path / "game"
    with pytest.raises(FileNotFoundError):
        verify(
            game_root / "Chaos Front_Data/resources.assets",
            baseline=True,
            meta_path=None,
            patch_path=None,
        )


def test_verify_reports_text_asset_discovery_error(tmp_path, monkeypatch):
    game_root = tmp_path / "game"
    data_dir = game_root / "Chaos Front_Data"
    data_dir.mkdir(parents=True)
    assets = data_dir / "resources.assets"
    assets.write_bytes(b"fake")
    env = FakeEnvironment([FakeTextAsset("UnitTypeData", "<UnitTypeData/>")])
    monkeypatch.setattr("tools.verify_tables.UnityPy.load", lambda _: env)

    with pytest.raises(TextAssetDiscoveryError):
        verify(assets, baseline=True, meta_path=None, patch_path=None)
