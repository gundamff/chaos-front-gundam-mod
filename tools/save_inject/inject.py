from __future__ import annotations

from copy import deepcopy
from typing import Any

from tools.common.es3 import get_value, set_value


def inject_v1(
    doc: dict[str, Any],
    *,
    unit_id: int = 93,
    character_id: int = 1121,
    exp: int = 0,
) -> dict[str, Any]:
    out = deepcopy(doc)
    chars = list(get_value(out, "PlayerCharacters"))
    exps = list(get_value(out, "PlayerCharacterEXPs"))
    if len(chars) != len(exps):
        raise ValueError(
            "PlayerCharacters and PlayerCharacterEXPs lengths differ; "
            "refusing to modify save"
        )

    unlocked = list(get_value(out, "PlayerUnlockedUnitTypes"))
    if unit_id not in unlocked:
        unlocked.append(unit_id)
    set_value(out, "PlayerUnlockedUnitTypes", unlocked)

    if character_id not in chars:
        chars.append(character_id)
        exps.append(20000)
    set_value(out, "PlayerCharacters", chars)
    set_value(out, "PlayerCharacterEXPs", exps)

    army_id = int(get_value(out, "PlayerArmyId"))
    units = list(get_value(out, "PlayerUnits"))
    already = any(u.get("unitType") == unit_id and u.get("characterId") == character_id for u in units)
    if not already:
        units.append(
            {
                "unitType": unit_id,
                "armyId": army_id,
                "characterId": character_id,
                "items": [],
                "custom": 0,
                "number": [0, 0],
                "exp": exp,
                "playerName": "",
            }
        )
    set_value(out, "PlayerUnits", units)
    return out
