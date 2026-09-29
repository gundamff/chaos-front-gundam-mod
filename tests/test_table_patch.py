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
        # fixtures only have character Index 84; keep fixture clone target
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
    assert meta["unit_id"] == 93
    assert meta["character_id"] == 1121
    assert meta["language_indices"]["unit_name"] == 3
    assert meta["language_indices"]["unit_info"] == 4
    assert meta["language_indices"]["char_name"] == 5
    assert meta["language_indices"]["char_info"] == 6


def test_apply_v1_tables_round_trip():
    patch = _fixture_patch()
    unit_src = (FIX / "sample_unittype_snippet.xml").read_text(encoding="utf-8")
    char_src = (FIX / "sample_character_snippet.xml").read_text(encoding="utf-8")
    lang_src = (FIX / "sample_language_snippet.xml").read_text(encoding="utf-8")

    units_in = xt.parse_items(unit_src)
    chars_in = xt.parse_items(char_src)
    langs_in = xt.parse_items(lang_src)

    u, c, l, meta = apply_v1_tables(unit_src, char_src, lang_src, patch)

    units = xt.parse_items(u)
    chars = xt.parse_items(c)
    langs = xt.parse_items(l)

    assert len(units) == len(units_in) + 1
    assert len(chars) == len(chars_in) + 1
    assert len(langs) == len(langs_in) + 4

    assert xt.find_item(units, 31) is not None
    assert xt.find_item(chars, 84) is not None

    unit = xt.find_item(units, 93)
    char = xt.find_item(chars, 1121)
    assert unit["Name"] == str(meta["language_indices"]["unit_name"])
    assert unit["Info"] == str(meta["language_indices"]["unit_info"])
    assert char["Name"] == str(meta["language_indices"]["char_name"])
    assert char["Info"] == str(meta["language_indices"]["char_info"])
    assert char["Portrait"] == xt.find_item(chars_in, 84)["Portrait"]

    for idx in meta["language_indices"].values():
        row = xt.find_item(langs, idx)
        assert row["CN"] != ""

    for doc in (u, c, l):
        assert doc.startswith('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>')
        assert "<MenuName>" in doc and doc.count("<MenuName>") == 1
        assert "</MenuName>" in doc
