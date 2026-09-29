# GBA export status

- **ROM:** Chinese patch `SD高达G世纪A汉化2.0_存档修复.gba` (32 MiB, title `GGENE A`)
- **Name markers:** no hits for RX-78 / 阿姆罗 / ガンダム / AMURO in utf-8/gbk/sjis/ascii (custom text encoding / pointer names)
- **Character table:** found at `0x1A6220`, stride `0x78` (120). Face id bytes match Chinese forum notes (Kira face `0x39`). Pointers at +0x08 are dialogue/script, **not** face graphics.
- **Compression:** almost no usable Nintendo LZ77 (`0x10`) graphics blobs with portrait-like sizes; raw 4bpp interpretation of random offsets yields noise.
- **Dumps:** exploratory PNGs under `raw/gba_research/` (entropy windows, mis-pointed “faces”) — **not** usable RX-78/Amuro art yet.
- **CF status:** gameplay vertical slice works with reused Model/Portrait; visual swap still blocked on (1) real GBA rip (2) Texture2D inject tool.

## Next options

1. **Manual rip:** open ROM in Tile Molester / YY-CHR, locate Amuro face + RX-78 map sprite, export PNG into `assets/`.
2. **Emulator dump:** mGBA/VBA view unit → dump OBJ/BG VRAM tiles.
3. **Temporary inject (B2):** after we have PNGs, overwrite reused slots `mapUnit31` / `portrait102` for a local visual test (also changes 异形斗兵/卡修斯 appearance).
4. **Proper inject (B1):** UABEA/AssetsTools.NET to add `mapUnit93` / `portrait170`.
