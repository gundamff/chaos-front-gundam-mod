"""Generate placeholder unit/portrait PNGs and assets/manifest.json."""

from __future__ import annotations

from pathlib import Path

from tools.common.paths import repo_root
from tools.gba_export.placeholders import generate as generate_assets


def generate(root: Path | None = None) -> dict[str, Path]:
    repo = root or repo_root()
    return generate_assets(repo / "assets")


def main() -> None:
    paths = generate()
    for name, path in paths.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
