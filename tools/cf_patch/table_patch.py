from __future__ import annotations

from tools.common import xml_tables as xt


def apply_v1_tables(
    unit_xml: str, char_xml: str, lang_xml: str, patch: dict
) -> tuple[str, str, str, dict]:
    units = xt.parse_items(unit_xml)
    chars = xt.parse_items(char_xml)
    langs = xt.parse_items(lang_xml)

    u_cfg = patch["unit"]
    c_cfg = patch["character"]

    langs, unit_name = xt.append_language(langs, note=u_cfg["note"], cn=u_cfg["name_cn"])
    langs, unit_info = xt.append_language(
        langs, note=f'{u_cfg["note"]}_info', cn=u_cfg["info_cn"]
    )
    langs, char_name = xt.append_language(langs, note=c_cfg["note"], cn=c_cfg["name_cn"])
    langs, char_info = xt.append_language(
        langs, note=f'{c_cfg["note"]}_info', cn=c_cfg["info_cn"]
    )

    template_u = xt.find_item(units, int(u_cfg["clone_from"]))
    template_c = xt.find_item(chars, int(c_cfg["clone_from"]))

    units.append(
        xt.clone_unit_item(
            template_u,
            new_id=int(u_cfg["id"]),
            name_idx=unit_name,
            info_idx=unit_info,
            note=u_cfg["note"],
            reuse_icon=bool(u_cfg.get("reuse_icon", True)),
        )
    )
    chars.append(
        xt.clone_character_item(
            template_c,
            new_id=int(c_cfg["id"]),
            name_idx=char_name,
            info_idx=char_info,
            note=c_cfg["note"],
            portrait=int(c_cfg["portrait"]),
        )
    )

    meta = {
        "unit_id": int(u_cfg["id"]),
        "character_id": int(c_cfg["id"]),
        "language_indices": {
            "unit_name": unit_name,
            "unit_info": unit_info,
            "char_name": char_name,
            "char_info": char_info,
        },
    }
    return (
        xt.render_items_document("UnitTypeData", units),
        xt.render_items_document("CharacterData", chars),
        xt.render_items_document("LanguageData", langs),
        meta,
    )
