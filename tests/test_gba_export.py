import json
from pathlib import Path

import pytest

from tools.gba_export.__main__ import main
from tools.gba_export.export import RomAnalysis, analyze_rom, find_rom, run_export
from tools.gba_export.placeholders import generate

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def test_find_rom_from_glob(tmp_path: Path):
    rom_dir = tmp_path / "rom"
    rom_dir.mkdir()
    rom = rom_dir / "test.gba"
    rom.write_bytes(b"\x00" * 64)
    assert find_rom(str(rom_dir / "*.gba"), tmp_path) == rom


def test_find_rom_missing(tmp_path: Path):
    assert find_rom(None, tmp_path) is None


def test_analyze_rom_header(tmp_path: Path):
    data = bytearray(512)
    data[0xA0:0xA7] = b"GGENE A"
    rom = tmp_path / "mini.gba"
    rom.write_bytes(data)
    analysis = analyze_rom(rom)
    assert analysis.title == "GGENE A"
    assert analysis.size == 512
    assert all(v is None for v in analysis.string_hits.values())


def test_run_export_without_rom_uses_placeholders(tmp_path: Path):
    assets = tmp_path / "assets"
    result = run_export(
        rom_arg=None,
        assets_dir=assets,
        raw_dir=tmp_path / "raw",
        repo=tmp_path,
    )
    assert result.used_placeholders
    assert (assets / "unit-93.png").read_bytes()[:8] == PNG_SIGNATURE
    assert (assets / "manifest.json").is_file()


def test_cli_no_rom_exits_zero_with_warning(capsys, tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["--out", str(tmp_path / "assets"), "--status-note", str(tmp_path / "note.md")]) == 0
    err = capsys.readouterr().err
    assert "USING_PLACEHOLDERS=1" in err


@pytest.mark.skipif(
    not any(Path(__file__).resolve().parents[1].joinpath("rom").glob("*.gba")),
    reason="local ROM not present",
)
def test_cli_with_local_rom():
    root = Path(__file__).resolve().parents[1]
    code = main(["--out", str(root / "assets")])
    assert code == 0
    manifest = json.loads((root / "assets" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["portrait_texture"] == "portrait170"


def test_generate_writes_manifest(tmp_path: Path):
    paths = generate(tmp_path)
    assert paths["manifest"].is_file()
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    assert manifest["files"]["unit"] == "assets/unit-93.png"
