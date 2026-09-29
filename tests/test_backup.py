from pathlib import Path

import pytest

from tools.cf_patch.backup import backup_resources, restore_backup


def _data_dir(game_root: Path) -> Path:
    return game_root / "Chaos Front_Data"


def test_backup_resources_copies_assets_and_resource_stream(tmp_path: Path):
    game_root = tmp_path / "game"
    data_dir = _data_dir(game_root)
    data_dir.mkdir(parents=True)
    (data_dir / "resources.assets").write_bytes(b"assets-original")
    (data_dir / "resources.assets.resS").write_bytes(b"stream-original")

    backup_dir = backup_resources(game_root, tmp_path / "backups")

    assert backup_dir.parent == tmp_path / "backups"
    assert (backup_dir / "resources.assets").read_bytes() == b"assets-original"
    assert (backup_dir / "resources.assets.resS").read_bytes() == b"stream-original"


def test_backup_resources_omits_missing_resource_stream(tmp_path: Path):
    game_root = tmp_path / "game"
    data_dir = _data_dir(game_root)
    data_dir.mkdir(parents=True)
    (data_dir / "resources.assets").write_bytes(b"assets-original")

    backup_dir = backup_resources(game_root, tmp_path / "backups")

    assert (backup_dir / "resources.assets").is_file()
    assert not (backup_dir / "resources.assets.resS").exists()


def test_backup_resources_requires_resources_assets(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="resources.assets"):
        backup_resources(tmp_path / "game", tmp_path / "backups")


def test_restore_backup_restores_assets_and_resource_stream(tmp_path: Path):
    game_root = tmp_path / "game"
    data_dir = _data_dir(game_root)
    data_dir.mkdir(parents=True)
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    (backup_dir / "resources.assets").write_bytes(b"assets-original")
    (backup_dir / "resources.assets.resS").write_bytes(b"stream-original")
    (data_dir / "resources.assets").write_bytes(b"assets-patched")
    (data_dir / "resources.assets.resS").write_bytes(b"stream-patched")

    restore_backup(backup_dir, game_root)

    assert (data_dir / "resources.assets").read_bytes() == b"assets-original"
    assert (data_dir / "resources.assets.resS").read_bytes() == b"stream-original"


def test_restore_backup_requires_resources_assets(tmp_path: Path):
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()

    with pytest.raises(FileNotFoundError, match="resources.assets"):
        restore_backup(backup_dir, tmp_path / "game")
