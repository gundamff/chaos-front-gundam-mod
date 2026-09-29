"""Research spike: locate GGA strings/tiles and dump candidate portrait PNGs."""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

from PIL import Image

ROM = Path(r"D:\eclipse\git\chaos-front-gundam-mod\rom")
OUT = Path(r"D:\eclipse\git\chaos-front-gundam-mod\raw\gba_research")


def find_rom() -> Path:
    matches = sorted(ROM.glob("*.gba"))
    if not matches:
        raise SystemExit("no rom")
    return matches[0]


def gba_lz77_decompress(data: bytes, offset: int) -> bytes | None:
    """Nintendo LZ77 (type 0x10). Returns None on failure."""
    if offset + 4 > len(data) or data[offset] != 0x10:
        return None
    size = data[offset + 1] | (data[offset + 2] << 8) | (data[offset + 3] << 16)
    if size <= 0 or size > 512 * 1024:
        return None
    src = offset + 4
    out = bytearray()
    try:
        while len(out) < size:
            if src >= len(data):
                return None
            flags = data[src]
            src += 1
            for bit in range(7, -1, -1):
                if len(out) >= size:
                    break
                if flags & (1 << bit):
                    if src + 1 >= len(data):
                        return None
                    b1, b2 = data[src], data[src + 1]
                    src += 2
                    disp = ((b1 & 0x0F) << 8) | b2
                    length = (b1 >> 4) + 3
                    start = len(out) - disp - 1
                    if start < 0:
                        return None
                    for i in range(length):
                        out.append(out[start + i])
                else:
                    out.append(data[src])
                    src += 1
        return bytes(out)
    except Exception:
        return None


def tiles_4bpp_to_image(tile_bytes: bytes, tiles_w: int, tiles_h: int, palette: list[tuple[int, int, int]]) -> Image.Image:
    w, h = tiles_w * 8, tiles_h * 8
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    tile_count = tiles_w * tiles_h
    need = tile_count * 32
    if len(tile_bytes) < need:
        tile_bytes = tile_bytes + bytes(need - len(tile_bytes))
    for t in range(tile_count):
        tx, ty = t % tiles_w, t // tiles_w
        base = t * 32
        for row in range(8):
            for col_pair in range(4):
                b = tile_bytes[base + row * 4 + col_pair]
                for nibble, dx in ((b & 0x0F, 0), (b >> 4, 1)):
                    x = tx * 8 + col_pair * 2 + dx
                    y = ty * 8 + row
                    if nibble == 0:
                        px[x, y] = (0, 0, 0, 0)
                    else:
                        r, g, bl = palette[nibble % len(palette)]
                        px[x, y] = (r, g, bl, 255)
    return img


def default_palette() -> list[tuple[int, int, int]]:
    # Distinct fake palette so shapes are visible without real pal
    return [
        (0, 0, 0),
        (255, 255, 255),
        (220, 40, 40),
        (40, 80, 220),
        (240, 200, 40),
        (40, 180, 80),
        (180, 80, 200),
        (40, 200, 220),
        (240, 140, 40),
        (120, 120, 120),
        (80, 40, 20),
        (200, 200, 200),
        (160, 100, 60),
        (100, 140, 200),
        (30, 30, 30),
        (250, 230, 180),
    ]


def read_palette_rgb5(data: bytes, offset: int, count: int = 16) -> list[tuple[int, int, int]] | None:
    if offset + count * 2 > len(data):
        return None
    out = []
    for i in range(count):
        v = struct.unpack_from("<H", data, offset + i * 2)[0]
        r = (v & 0x1F) * 8
        g = ((v >> 5) & 0x1F) * 8
        b = ((v >> 10) & 0x1F) * 8
        out.append((r, g, b))
    return out


def main() -> None:
    rom = find_rom()
    data = rom.read_bytes()
    OUT.mkdir(parents=True, exist_ok=True)
    report: list[str] = [f"rom={rom.name} size={len(data)}"]

    needles = [
        ("sjis:ガンダム", "ガンダム".encode("shift_jis")),
        ("sjis:アムロ", "アムロ".encode("shift_jis")),
        ("sjis:RX-78", "RX-78".encode("shift_jis")),
        ("ascii:GUNDAM", b"GUNDAM"),
        ("ascii:AMURO", b"AMURO"),
        ("ascii:RX-78", b"RX-78"),
        ("gbk:高达", "高达".encode("gbk")),
        ("gbk:阿姆罗", "阿姆罗".encode("gbk")),
    ]
    hits = {}
    for name, needle in needles:
        idx = data.find(needle)
        hits[name] = idx
        report.append(f"hit {name} = {hex(idx) if idx >= 0 else None}")

    # Character table region from Chinese forum (Kira ~ 0x1A6220)
    char_base = 0x1A6220
    report.append(f"char_base_snip={data[char_base:char_base+64].hex()}")

    # Dump raw windows around char base as 4bpp sheets for visual hunt
    pal = default_palette()
    for label, off, tw, th in [
        ("near_char_1a6220", char_base, 16, 16),
        ("near_char_1a5000", 0x1A5000, 16, 16),
        ("gfx_080000", 0x080000, 16, 16),
        ("gfx_100000", 0x100000, 16, 16),
        ("gfx_200000", 0x200000, 16, 16),
        ("gfx_300000", 0x300000, 16, 16),
    ]:
        chunk = data[off : off + tw * th * 32]
        img = tiles_4bpp_to_image(chunk, tw, th, pal)
        path = OUT / f"{label}_{hex(off)}.png"
        img.save(path)
        report.append(f"dump {path.name}")

    # Try LZ77 scan in a limited range for decompressible graphics-sized blobs
    lz_hits = 0
    for off in range(0, min(len(data), 0x400000), 0x100):
        if data[off] != 0x10:
            continue
        dec = gba_lz77_decompress(data, off)
        if not dec or len(dec) < 32 * 16:
            continue
        # Prefer sizes that look like tile sheets (multiple of 32)
        if len(dec) % 32 != 0:
            continue
        tiles = len(dec) // 32
        if tiles < 16 or tiles > 1024:
            continue
        tw = 16
        th = max(1, min(32, tiles // tw))
        img = tiles_4bpp_to_image(dec[: tw * th * 32], tw, th, pal)
        path = OUT / f"lz77_{hex(off)}_t{tiles}.png"
        img.save(path)
        lz_hits += 1
        report.append(f"lz77 {hex(off)} size={len(dec)} -> {path.name}")
        if lz_hits >= 40:
            break

    (OUT / "report.txt").write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report[:30]))
    print(f"... wrote {OUT}")


if __name__ == "__main__":
    main()
