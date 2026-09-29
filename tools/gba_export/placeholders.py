"""Generate labeled placeholder unit/portrait PNGs and manifest.json."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZE = 64
BG = (48, 48, 64)
FG = (220, 220, 240)


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


def generate(assets_dir: Path) -> dict[str, Path]:
    unit = assets_dir / "unit-93.png"
    portrait = assets_dir / "portrait-170.png"
    _make_label_png("RX78", unit)
    _make_label_png("AMURO", portrait)
    manifest = write_manifest(assets_dir)
    return {"unit": unit, "portrait": portrait, "manifest": manifest}
