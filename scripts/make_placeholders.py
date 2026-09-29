"""Generate placeholder unit/portrait PNGs and assets/manifest.json."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZE = 64
BG = (48, 48, 64)
FG = (220, 220, 240)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _make_label_png(label: str, path: Path) -> None:
    img = Image.new("RGB", (SIZE, SIZE), BG)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), label, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((SIZE - tw) // 2, (SIZE - th) // 2), label, fill=FG, font=font)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG", optimize=True)


def write_manifest(assets_dir: Path) -> Path:
    manifest = {
        "unit_texture_candidates": ["mapUnit93", "mapUnit93_0"],
        "portrait_texture": "portrait170",
        "files": {
            "unit": "assets/unit-93.png",
            "portrait": "assets/portrait-170.png",
        },
    }
    path = assets_dir / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def generate(root: Path | None = None) -> dict[str, Path]:
    repo = root or _repo_root()
    assets = repo / "assets"
    unit = assets / "unit-93.png"
    portrait = assets / "portrait-170.png"
    _make_label_png("RX78", unit)
    _make_label_png("AMURO", portrait)
    manifest = write_manifest(assets)
    return {"unit": unit, "portrait": portrait, "manifest": manifest}


def main() -> None:
    paths = generate()
    for name, path in paths.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
