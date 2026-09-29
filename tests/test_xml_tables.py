from pathlib import Path

from tools.common import xml_tables as xt

FIX = Path(__file__).parent / "fixtures"


def test_append_language_returns_next_index():
    xml = (FIX / "sample_language_snippet.xml").read_text(encoding="utf-8")
    items = xt.parse_items(xml)
    new_items, idx = xt.append_language(items, note="RX", cn="RX-78-2")
    assert idx == 3
    assert new_items[-1]["CN"] == "RX-78-2"
    assert new_items[-1]["Index"] == "3"


def test_clone_unit_overrides_ids_and_names():
    xml = (FIX / "sample_unittype_snippet.xml").read_text(encoding="utf-8")
    template = xt.find_item(xt.parse_items(xml), 31)
    cloned = xt.clone_unit_item(
        template,
        new_id=93,
        name_idx=6059,
        info_idx=6060,
        note="RX-78-2",
        reuse_icon=True,
        reuse_model=False,
    )
    assert cloned["Index"] == "93"
    assert cloned["Model"] == "93"
    assert cloned["Name"] == "6059"
    assert cloned["Info"] == "6060"
    assert cloned["Icon"] == "31"  # reuse
    assert cloned["Weapon1"] == "7"
    assert cloned["Note"] == "RX-78-2"

    reused = xt.clone_unit_item(
        template,
        new_id=93,
        name_idx=6059,
        info_idx=6060,
        note="RX-78-2",
        reuse_icon=True,
        reuse_model=True,
    )
    assert reused["Model"] == "31"


def test_clone_character_sets_portrait():
    xml = (FIX / "sample_character_snippet.xml").read_text(encoding="utf-8")
    template = xt.find_item(xt.parse_items(xml), 84)
    cloned = xt.clone_character_item(
        template,
        new_id=1121,
        name_idx=6061,
        info_idx=6062,
        note="阿姆罗",
        portrait=170,
        reuse_portrait=False,
    )
    assert cloned["Index"] == "1121"
    assert cloned["Portrait"] == "170"
    assert cloned["Name"] == "6061"

    reused = xt.clone_character_item(
        template,
        new_id=1121,
        name_idx=6061,
        info_idx=6062,
        note="阿姆罗",
        reuse_portrait=True,
    )
    assert reused["Portrait"] == template["Portrait"]


def test_insert_items_preserves_declaration_and_menuname():
    xml = (FIX / "sample_unittype_snippet.xml").read_text(encoding="utf-8")
    template = xt.find_item(xt.parse_items(xml), 31)
    cloned = xt.clone_unit_item(
        template,
        new_id=93,
        name_idx=6059,
        info_idx=6060,
        note="RX-78-2",
        reuse_icon=True,
    )
    out = xt.insert_items(xml, [cloned])
    assert out.startswith('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>')
    assert "<MenuName>" in out and "</MenuName>" in out
    assert out.count("<MenuName>") == 1
    assert 'Index="31"' in out and 'Index="93"' in out
    assert out.index('Index="31"') < out.index('Index="93"')
    assert out.index('Index="93"') < out.index("</MenuName>")
