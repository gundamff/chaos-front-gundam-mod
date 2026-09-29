from __future__ import annotations

from pathlib import Path

DEFAULT_GAME = Path(r"F:\SteamLibrary\steamapps\common\Chaos Front")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_game_root() -> Path:
    return DEFAULT_GAME


def game_data_dir(game_root: Path | None = None) -> Path:
    root = game_root or default_game_root()
    return root / "Chaos Front_Data"


def resources_assets(game_root: Path | None = None) -> Path:
    return game_data_dir(game_root) / "resources.assets"
