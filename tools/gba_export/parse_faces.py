"""Parse GGA character table and dump face graphics by face id."""
from __future__ import annotations

import struct
from pathlib import Path

from PIL import Image

from tools.gba_export.research_dump import (
    default_palette,
    find_rom,
    tiles_4bpp_to_image,
)

OUT = Path(r"D:\eclipse\git\chaos-front-gundam-mod\raw\gba_research")


def main() -> None:
    data = find_rom().read_bytes()
    base = 0x1A6220
    # Discover stride: consecutive entries with face bytes XX XX 00 00 and GBA ptr
    best = None
    for stride in range(0x20, 0x80, 4):
        ok = 0
        for i in range(20):
            o = base + i * stride
            face_pad = data[o + 6 : o + 8]
            ptr = struct.unpack_from("<I", data, o + 8)[0]
            if face_pad == b"\x00\x00" and 0x08000000 <= ptr < 0x0A000000:
                ok += 1
        if best is None or ok > best[0]:
            best = (ok, stride)
    print("best stride", best)

    stride = best[1]
    entries = []
    for i in range(400):
        o = base + i * stride
        if o + stride > len(data):
            break
        face = data[o + 4]
        face2 = data[o + 5]
        ptr = struct.unpack_from("<I", data, o + 8)[0]
        if not (0x08000000 <= ptr < 0x0A000000):
            # stop when pointer pattern breaks for a while
            if i > 5 and face == 0 and face2 == 0:
                continue
        entries.append({"i": i, "off": o, "face": face, "face2": face2, "ptr": ptr})

    print("entries", len(entries), "first faces", [e["face"] for e in entries[:30]])

    # Face graphics: often table of pointers indexed by face id
    # Search for pointer table containing many 08xxxxxx values near graphics
    # Heuristic: dump tiles at ptr-0x08000000 for first few faces
    pal = default_palette()
    OUT.mkdir(parents=True, exist_ok=True)
    for e in entries[:12]:
        file_off = e["ptr"] - 0x08000000
        if file_off < 0 or file_off >= len(data):
            continue
        # try interpret pointer target as 4bpp tiles 8x8 sheet (face ~ 32x32 = 4x4 tiles = 512 bytes)
        for tw, th, tag in [(4, 4, "32"), (8, 8, "64"), (4, 8, "32x64")]:
            chunk = data[file_off : file_off + tw * th * 32]
            img = tiles_4bpp_to_image(chunk, tw, th, pal)
            img.save(OUT / f"face_i{e['i']}_id{e['face']}_p{hex(file_off)}_{tag}.png")

    # Also try: face id indexes into a graphics bank
    # Scan for densest GBA pointer arrays
    ptr_arrays = []
    for off in range(0, len(data) - 4 * 200, 4):
        good = 0
        for j in range(200):
            p = struct.unpack_from("<I", data, off + j * 4)[0]
            if 0x08000000 <= p < 0x0A000000:
                good += 1
            else:
                break
        if good >= 80:
            ptr_arrays.append((good, off))
            # skip ahead
    ptr_arrays.sort(reverse=True)
    print("top pointer arrays", [(hex(o), n) for n, o in ptr_arrays[:10]])

    # If we find an array, dump face 0x39 (kira) entry
    for count, off in ptr_arrays[:5]:
        # assume index = face id
        for face_id in (0x39, 0x01, 0x02, 57):
            if face_id >= count:
                continue
            p = struct.unpack_from("<I", data, off + face_id * 4)[0]
            fo = p - 0x08000000
            if not (0 <= fo < len(data) - 512):
                continue
            img = tiles_4bpp_to_image(data[fo : fo + 4 * 4 * 32], 4, 4, pal)
            img.save(OUT / f"arr_{hex(off)}_face{face_id}_{hex(fo)}.png")
            print("dumped", hex(off), "face", face_id, "->", hex(fo))


if __name__ == "__main__":
    main()
