"""Find face-id → graphics pointer table and dump portraits."""
from __future__ import annotations

import struct
from pathlib import Path

from tools.gba_export.research_dump import (
    default_palette,
    find_rom,
    gba_lz77_decompress,
    tiles_4bpp_to_image,
)

OUT = Path(r"D:\eclipse\git\chaos-front-gundam-mod\raw\gba_research\face_bank")


def looks_like_ptr_table(data: bytes, off: int, count: int = 128) -> bool:
    if off + count * 4 > len(data):
        return False
    prev = -1
    good = 0
    for i in range(count):
        p = struct.unpack_from("<I", data, off + i * 4)[0]
        if not (0x08000000 <= p < 0x0A000000):
            return False
        fo = p - 0x08000000
        if fo >= len(data):
            return False
        # Prefer mostly increasing pointers (common for packed gfx banks)
        if p >= prev:
            good += 1
        prev = p
    return good >= count * 0.7


def main() -> None:
    data = find_rom().read_bytes()
    OUT.mkdir(parents=True, exist_ok=True)
    pal = default_palette()

    # Collect used face ids from character table
    base, stride = 0x1A6220, 120
    face_ids = []
    for i in range(300):
        o = base + i * stride
        face_ids.append(data[o + 4])
    max_face = max(face_ids)
    print("face ids sample", face_ids[:20], "max", max_face)

    candidates = []
    step = 4
    for off in range(0, len(data) - max_face * 4 - 4, step):
        # quick reject: pointer at index 57 must be valid GBA ptr
        p57 = struct.unpack_from("<I", data, off + 57 * 4)[0]
        if not (0x08000000 <= p57 < 0x0A000000):
            continue
        if not looks_like_ptr_table(data, off, min(128, max_face + 1)):
            continue
        candidates.append(off)
        if len(candidates) >= 30:
            # don't scan whole ROM forever if dense; jump ahead
            pass
        if len(candidates) >= 80:
            break

    print("candidate tables", len(candidates), [hex(c) for c in candidates[:20]])

    # Score candidates: decompress/raw at face 57 yields non-empty variance
    scored = []
    for off in candidates[:40]:
        p = struct.unpack_from("<I", data, off + 57 * 4)[0]
        fo = p - 0x08000000
        dec = gba_lz77_decompress(data, fo)
        src = dec if dec else data[fo : fo + 2048]
        if len(src) < 256:
            continue
        # variance score
        score = len(set(src[:512]))
        scored.append((score, off, fo, bool(dec), len(src) if dec else 0))
    scored.sort(reverse=True)
    print("top scored", scored[:10])

    if not scored:
        print("no scored candidates")
        return

    best = scored[0][1]
    print("using table", hex(best))
    # Dump faces 1..80 and specifically known range including Amuro search later
    for face in list(range(1, 81)) + [57, 58, 59]:
        p = struct.unpack_from("<I", data, best + face * 4)[0]
        fo = p - 0x08000000
        dec = gba_lz77_decompress(data, fo)
        src = dec if dec and len(dec) >= 512 else data[fo : fo + 4 * 4 * 32]
        tag = "lz" if dec and len(dec) >= 512 else "raw"
        # try 32x32 and 64x64
        for tw, th in [(4, 4), (8, 8)]:
            need = tw * th * 32
            if len(src) < need:
                continue
            img = tiles_4bpp_to_image(src[:need], tw, th, pal)
            img.save(OUT / f"face{face:03d}_{tag}_{tw*8}.png")

    (OUT / "table_offset.txt").write_text(hex(best), encoding="utf-8")


if __name__ == "__main__":
    main()
