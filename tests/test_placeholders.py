import json
from pathlib import Path

from tools.common.paths import repo_root

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

ASSETS = repo_root() / "assets"
MANIFEST = ASSETS / "manifest.json"
UNIT_PNG = ASSETS / "unit-93.png"
PORTRAIT_PNG = ASSETS / "portrait-170.png"


def _assert_valid_png(path: Path) -> None:
    assert path.is_file(), f"missing: {path}"
    data = path.read_bytes()
    assert len(data) > 0, f"empty: {path}"
    assert data[:8] == PNG_SIGNATURE, f"not a PNG: {path}"


def test_placeholder_pngs_exist_and_are_valid():
    _assert_valid_png(UNIT_PNG)
    _assert_valid_png(PORTRAIT_PNG)


def test_manifest_structure():
    assert MANIFEST.is_file()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["unit_texture_candidates"] == ["mapUnit93", "mapUnit93_0"]
    assert manifest["portrait_texture"] == "portrait170"
    assert manifest["files"]["unit"] == "assets/unit-93.png"
    assert manifest["files"]["portrait"] == "assets/portrait-170.png"
