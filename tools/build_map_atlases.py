"""Build CF mapUnit-style 768x576 atlases (12x9 of 64) from Genesis direction frames.

Layout (matches vanilla mapUnit31):
- Rows 0-7: team-color slots (we repeat the same art)
- Row 8: white flash silhouettes (cols 0-7)
- Within a row: cols 0-3 = 4 dirs; cols 4-7 and 8-11 = copies
- Dir pairs (0,1) and (2,3) are left/right mirrors in vanilla; we do the same
  when only two base angles are available.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "raw" / "genesis_processed"
CONTENT = ROOT / "plugins" / "CfGundamMod" / "content"

CELL = 64
COLS = 12
ROWS = 9
ART_MAX = 52


def trim_alpha(im: Image.Image, pad: int = 1) -> Image.Image:
    im = im.convert("RGBA")
    bbox = im.getbbox()
    if not bbox:
        return im
    l, t, r, b = bbox
    return im.crop(
        (max(0, l - pad), max(0, t - pad), min(im.width, r + pad), min(im.height, b + pad))
    )


def fit_cell(
    src: Image.Image,
    art_max: int = ART_MAX,
    y_off: int = 4,
) -> Image.Image:
    """PIL y=0 is TOP; positive y_off moves art DOWN into the map hex base."""
    art = trim_alpha(src.convert("RGBA"))
    canvas = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
    scale = min(art_max / art.width, art_max / art.height)
    nw = max(1, int(round(art.width * scale)))
    nh = max(1, int(round(art.height * scale)))
    resized = art.resize((nw, nh), Image.Resampling.LANCZOS)
    dx = (CELL - nw) // 2
    dy = (CELL - nh) // 2 + y_off
    dy = max(0, min(CELL - nh, dy))
    canvas.alpha_composite(resized, (dx, dy))
    return canvas


def white_silhouette(cell: Image.Image) -> Image.Image:
    out = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
    px = cell.load()
    op = out.load()
    for y in range(CELL):
        for x in range(CELL):
            a = px[x, y][3]
            if a > 40:
                op[x, y] = (255, 255, 255, a)
    return out


def four_dirs(
    a: Image.Image,
    b: Image.Image,
    art_max: int = ART_MAX,
    y_off: int = 4,
) -> list[Image.Image]:
    """Two base angles → four CF dirs via horizontal flip."""
    d0 = fit_cell(a, art_max=art_max, y_off=y_off)
    d1 = d0.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    d2 = fit_cell(b, art_max=art_max, y_off=y_off)
    d3 = d2.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    return [d0, d1, d2, d3]


def four_dirs_distinct(
    frames: list[Image.Image],
    art_max: int = ART_MAX,
    y_off: int = 4,
) -> list[Image.Image]:
    assert len(frames) >= 4
    return [fit_cell(frames[i], art_max=art_max, y_off=y_off) for i in range(4)]


def build_atlas(dirs: list[Image.Image]) -> Image.Image:
    assert len(dirs) == 4
    atlas = Image.new("RGBA", (COLS * CELL, ROWS * CELL), (0, 0, 0, 0))
    for row in range(8):
        for d, cell in enumerate(dirs):
            for copy in range(3):
                col = d + copy * 4
                atlas.paste(cell, (col * CELL, row * CELL), cell)
    whites = [white_silhouette(c) for c in dirs]
    for d, cell in enumerate(whites):
        for copy in range(2):  # vanilla row8 fills cols 0-7
            col = d + copy * 4
            atlas.paste(cell, (col * CELL, 8 * CELL), cell)
    return atlas


def load(name: str) -> Image.Image:
    return Image.open(PROC / name).convert("RGBA")


def main() -> None:
    CONTENT.mkdir(parents=True, exist_ok=True)
    PROC.mkdir(parents=True, exist_ok=True)

    # Prefer band11 re-extracts when present (fuller head); fall back to older fr*.
    zaku_front = "zaku_map_fr1.png" if (PROC / "zaku_map_fr1.png").exists() else "zaku_fr1.png"
    zaku_rear = "zaku_map_fr0.png" if (PROC / "zaku_map_fr0.png").exists() else "zaku_fr4.png"

    jobs = {
        # Idle on CF map = directional standing (no separate walk track in atlas).
        # Do NOT use walk/dash frames (e.g. rx78_map_fr6) — idle would look mid-stride.
        "map-rx78.png": four_dirs(
            load("rx78-front-raw.png"), load("rx78_map_fr0.png"), art_max=50, y_off=6
        ),
        # Zaku: between "scalp clipped" (y_off~4) and "too low" (y_off=14)
        "map-zaku2.png": four_dirs(
            load(zaku_front), load(zaku_rear), art_max=42, y_off=9
        ),
        "map-elmeth.png": four_dirs_distinct(
            [load("elmeth_q0.png"), load("elmeth_q1.png"), load("elmeth_q2.png"), load("elmeth_q3.png")],
            art_max=50,
            y_off=6,
        ),
        "map-whitebase.png": four_dirs_distinct(
            [load("wb_map_fr0.png"), load("wb_map_fr1.png"), load("wb_map_fr2.png"), load("wb_map_fr3.png")],
            art_max=50,
            y_off=6,
        ),
    }

    for name, dirs in jobs.items():
        atlas = build_atlas(dirs)
        path = CONTENT / name
        atlas.save(path)
        strip = Image.new("RGBA", (CELL * 4, CELL), (0, 0, 0, 0))
        for i, c in enumerate(dirs):
            strip.paste(c, (i * CELL, 0), c)
        strip.save(PROC / f"preview_{name}")
        # opaque vertical span for tuning
        cell0 = dirs[0]
        top = next((y for y in range(CELL) if any(cell0.getpixel((x, y))[3] > 40 for x in range(CELL))), None)
        bot = next((y for y in range(CELL - 1, -1, -1) if any(cell0.getpixel((x, y))[3] > 40 for x in range(CELL))), None)
        print(f"wrote {path} {atlas.size} dir0 opaque y={top}..{bot}")


if __name__ == "__main__":
    main()
