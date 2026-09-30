"""Process Genesis One Year War dumps into CF-ready portrait/unit icons."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "raw" / "Nintendo Switch - SD Gundam G Generation Genesis" / "Mobile Suite Gundam"
OUT = ROOT / "raw" / "genesis_processed"
CONTENT = ROOT / "plugins" / "CfGundamMod" / "content"
PLUGIN_CONTENT = Path(
    r"F:\SteamLibrary\steamapps\common\Chaos Front\BepInEx\plugins\CfGundamMod"
)


def trim_alpha(im: Image.Image, pad: int = 2) -> Image.Image:
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    bbox = im.getbbox()
    if not bbox:
        return im
    l, t, r, b = bbox
    l = max(0, l - pad)
    t = max(0, t - pad)
    r = min(im.width, r + pad)
    b = min(im.height, b + pad)
    return im.crop((l, t, r, b))


def compose_portrait_200x160(
    src: Image.Image,
    top_pad: int = 32,
    max_w: int = 72,
    max_h: int = 88,
    nudge_x: int = 2,
) -> Image.Image:
    """CF 200x160 胸像 — sized for ~48 mask + formation strip.

    Vanilla portraits fill the canvas as painted busts; Genesis Amuro is a
    tight helmet close-up. Filling 140px+ makes the 48 mask show only an eye
    and the strip show a helmet sliver. Keep art ~72x88 (TextureCache / CF
    head-shoulder scale) with top_pad so the face sits where Shift(4,-15) looks.
    """
    bust = trim_alpha(src.convert("RGBA"))
    canvas = Image.new("RGBA", (200, 160), (0, 0, 0, 255))
    scale = min(max_w / bust.width, max_h / bust.height)
    nw = max(1, int(round(bust.width * scale)))
    nh = max(1, int(round(bust.height * scale)))
    # Soft downsample then snap to pixel look (closer to CF portrait palette)
    resized = bust.resize((nw, nh), Image.Resampling.LANCZOS)
    dx = (200 - nw) // 2 + nudge_x
    dy = top_pad
    if dx < 2:
        dx = 2
    if dx + nw > 198:
        dx = 198 - nw
    if dy + nh > 158:
        dy = max(0, 158 - nh)
    canvas.alpha_composite(resized, (dx, dy))
    out = Image.new("RGB", (200, 160), (0, 0, 0))
    out.paste(canvas, mask=canvas.split()[-1])
    return out


def compose_unit_64(src: Image.Image, art: int = 40, y_off: int = 7, nudge_x: int = -1) -> Image.Image:
    """64x64 — PIL y=0 is TOP, positive y_off moves art DOWN into the hex base.

    Defaults align with vanilla mapUnit/unitIcon feel: long edge ~40px,
    mildly dropped into the hex (bbox cy ≈ 38–40).
    """
    icon = trim_alpha(src.convert("RGBA"))
    canvas = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    scale = min(art / icon.width, art / icon.height)
    nw = max(1, int(round(icon.width * scale)))
    nh = max(1, int(round(icon.height * scale)))
    resized = icon.resize((nw, nh), Image.Resampling.LANCZOS)
    dx = (64 - nw) // 2 + nudge_x
    dy = (64 - nh) // 2 + y_off
    dy = max(0, min(64 - nh, dy))
    dx = max(0, min(64 - nw, dx))
    canvas.alpha_composite(resized, (dx, dy))
    return canvas


def find_rx78_on_sheet(sheet: Image.Image) -> Image.Image | None:
    """Heuristic: sheet is tall strip of map units; find bright white/blue/red Gundam-ish tile.
    Fallback: crop first non-empty tile grid if layout is regular.
    """
    # Try common Genesis map unit cell sizes by scanning non-empty regions
    # Simpler approach: export a few candidate crops from top of sheet for manual pick,
    # and also search for RX-78 by looking at known grid.
    # Many G Gen sheets stack units vertically with fixed cell height.
    w, h = sheet.size
    # Guess cell width = sheet width (single column) or multi-column
    # This sheet is 1668 wide x 5969 tall from metadata — likely multi-column atlas.
    # Split into grid of ~128 or ~256 cells and pick by color signature (white+red+yellow eyes).
    for cell in (128, 96, 160, 192, 256, 64, 80):
        if w % cell != 0:
            continue
        cols = w // cell
        rows = h // cell
        if rows < 2:
            continue
        best = None
        best_score = -1
        for row in range(min(rows, 40)):
            for col in range(cols):
                tile = sheet.crop((col * cell, row * cell, (col + 1) * cell, (row + 1) * cell))
                score = gundam_score(tile)
                if score > best_score:
                    best_score = score
                    best = (tile, row, col, cell, score)
        if best and best[4] > 50:
            print(f"RX-78 candidate cell={best[3]} row={best[1]} col={best[2]} score={best[4]}")
            return trim_alpha(best[0].convert("RGBA"))
    return None


def gundam_score(tile: Image.Image) -> float:
    """Score how RX-78-like: white body + red accent + yellow."""
    t = tile.convert("RGBA").resize((32, 32), Image.Resampling.NEAREST)
    px = list(t.getdata())
    white = red = yellow = opaque = 0
    for r, g, b, a in px:
        if a < 40:
            continue
        opaque += 1
        if r > 200 and g > 200 and b > 200:
            white += 1
        if r > 180 and g < 90 and b < 90:
            red += 1
        if r > 180 and g > 150 and b < 80:
            yellow += 1
    if opaque < 40:
        return -1
    return white * 1.0 + red * 3.0 + yellow * 2.5


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    CONTENT.mkdir(parents=True, exist_ok=True)

    amuro = SRC / "0010 Mobile Suite Gundam" / "G0010C00100_0.png"
    if not amuro.exists():
        raise SystemExit(f"missing Amuro: {amuro}")

    portrait = compose_portrait_200x160(Image.open(amuro))
    portrait_path = OUT / "portrait-amuro-200x160.png"
    portrait.save(portrait_path)
    print("wrote", portrait_path, portrait.size)

    # Also save a couple emotion variants for review
    for i in (1, 2, 9):
        p = SRC / "0010 Mobile Suite Gundam" / f"G0010C00100_{i}.png"
        if p.exists():
            compose_portrait_200x160(Image.open(p)).save(OUT / f"portrait-amuro-alt{i}.png")

    units_sheet = next(SRC.glob("*Units - Mobile Suite Gundam.png"), None)
    unit_icon = None
    if units_sheet:
        print("units sheet", units_sheet, Image.open(units_sheet).size)
        # Row0 strip: frames are facing dirs; f1 is front RX-78 with rifle+shield
        sheet = Image.open(units_sheet).convert("RGBA")
        # Re-extract block0 using same heuristic as before
        strip = sheet.crop((0, 4, sheet.width, 96))
        empty_set = set()
        for x in range(strip.width):
            if sum(1 for y in range(strip.height) if strip.getpixel((x, y))[3] > 30) < 2:
                empty_set.add(x)
        spans = []
        in_content = False
        start = 0
        for x in range(strip.width):
            empty = x in empty_set
            if not empty and not in_content:
                in_content = True
                start = x
            elif empty and in_content:
                in_content = False
                if x - start > 20:
                    spans.append((start, x))
        if in_content and strip.width - start > 20:
            spans.append((start, strip.width))
        print("row0 frames", len(spans))
        if len(spans) > 1:
            a, b = spans[1]
            unit_icon = trim_alpha(strip.crop((a, 0, b, strip.height)))
            unit_icon.save(OUT / "rx78-front-raw.png")
            print("RX-78 front", unit_icon.size)

    if unit_icon is None:
        print("WARN: RX-78 auto-pick failed; keeping previous unit-rx78.png")
    else:
        icon64 = compose_unit_64(unit_icon)
        icon_path = OUT / "unit-rx78-64.png"
        icon64.save(icon_path)
        print("wrote", icon_path)

    # Deploy
    dests = [CONTENT, PLUGIN_CONTENT]
    for d in dests:
        if not d.exists():
            continue
        portrait.save(d / "portrait-amuro.png")
        print("deployed portrait ->", d)
        if unit_icon is not None:
            compose_unit_64(unit_icon).save(d / "unit-rx78.png")
            print("deployed unit ->", d)


if __name__ == "__main__":
    main()
