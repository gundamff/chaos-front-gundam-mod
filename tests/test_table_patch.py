from pathlib import Path

import yaml

from tools.cf_patch.table_patch import apply_v1_tables
from tools.common import xml_tables as xt

FIX = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).parent.parent


def _fixture_patch():
    patch = yaml.safe_load((ROOT / "patches/v1-rx78.yaml").read_text(encoding="utf-8"))
    return {
        **patch,
        "unit": {**patch["unit"], "clone_from": 31},
        "character": {**patch["character"], "clone_from": 84},
    }


def test_apply_v1_tables_appends_four_language_rows():
    patch = _fixture_patch()
    u, c, l, meta = apply_v1_tables(
        (FIX / "sample_unittype_snippet.xml").read_text(encoding="utf-8"),
        (FIX / "sample_character_snippet.xml").read_text(encoding="utf-8"),
        (FIX / "sample_language_snippet.xml").read_text(encoding="utf-8"),
        patch,
    )
    assert 'Index="93"' in u
    assert 'Index="1121"' in c
    assert meta["language_indices"]["unit_name"] == 3
    assert meta["language_indices"]["unit_info"] == 4
    assert meta["language_indices"]["char_name"] == 5
    assert meta["language_indices"]["char_info"] == 6


def test_apply_v1_tables_round_trip():
    patch = _fixture_patch()
    unit_src = (FIX / "sample_unittype_snippet.xml").read_text(encoding="utf-8")
    char_src = (FIX / "sample_character_snippet.xml").read_text(encoding="utf-8")
    lang_src = (FIX / "sample_language_snippet.xml").read_text(encoding="utf-8")

    u, c, l, meta = apply_v1_tables(unit_src, char_src, lang_src, patch)

    units = xt.parse_items(u)
    chars = xt.parse_items(c)
    langs = xt.parse_items(l)

    assert xt.find_item(units, 93)["Name"] == str(meta["language_indices"]["unit_name"])
    assert xt.find_item(chars, 1121)["Name"] == str(meta["language_indices"]["char_name"])
    for idx in meta["language_indices"].values():
        row = xt.find_item(langs, idx)
        assert row["CN"] != ""
