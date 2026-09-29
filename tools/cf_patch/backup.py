from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import shutil
import tempfile

from tools.common.paths import game_data_dir, resources_assets


_RESOURCE_FILES = ("resources.assets", "resources.assets.resS")


def backup_resources(game_root: Path, backups_dir: Path) -> Path:
    game_root = Path(game_root)
    source_assets = resources_assets(game_root)
    if not source_assets.is_file():
        raise FileNotFoundError(f"resources.assets not found: {source_assets}")

    backups_dir = Path(backups_dir)
    backup_dir = backups_dir / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_dir.mkdir(parents=True)

    source_dir = game_data_dir(game_root)
    for name in _RESOURCE_FILES:
        source = source_dir / name
        if source.is_file():
            shutil.copy2(source, backup_dir / name)
    return backup_dir


def restore_backup(backup_dir: Path, game_root: Path) -> None:
    backup_dir = Path(backup_dir)
    source_assets = backup_dir / "resources.assets"
    if not source_assets.is_file():
        raise FileNotFoundError(f"resources.assets not found in backup: {source_assets}")

    destination_dir = game_data_dir(Path(game_root))
    destination_dir.mkdir(parents=True, exist_ok=True)
    for name in _RESOURCE_FILES:
        source = backup_dir / name
        if source.is_file():
            destination = destination_dir / name
            file_descriptor, staged_name = tempfile.mkstemp(
                prefix=f".{name}.", suffix=".tmp", dir=destination_dir
            )
            os.close(file_descriptor)
            staged = Path(staged_name)
            try:
                shutil.copy2(source, staged)
                os.replace(staged, destination)
            finally:
                staged.unlink(missing_ok=True)
