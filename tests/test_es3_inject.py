import json
from pathlib import Path

from tools.common.es3 import get_value, parse_es3, stringify_es3
from tools.save_inject.inject import inject_v1

FIXTURE = Path(__file__).parent / "fixtures" / "minimal-save.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_inject_v1_unlocks_unit_and_character():
    doc = _load_fixture()
    out = inject_v1(doc, unit_id=93, character_id=1121)

    unlocked = get_value(out, "PlayerUnlockedUnitTypes")
    assert 93 in unlocked

    chars = get_value(out, "PlayerCharacters")
    assert 1121 in chars

    units = get_value(out, "PlayerUnits")
    matches = [u for u in units if u.get("unitType") == 93 and u.get("characterId") == 1121]
    assert len(matches) == 1
    assert matches[0]["armyId"] == 12


def test_inject_v1_round_trip_preserves_player_army_id():
    doc = _load_fixture()
    army_before = get_value(doc, "PlayerArmyId")

    out = inject_v1(doc, unit_id=93, character_id=1121)
    text = stringify_es3(out)
    round_tripped = parse_es3(text)

    assert get_value(round_tripped, "PlayerArmyId") == army_before


def test_inject_v1_idempotent():
    doc = _load_fixture()
    once = inject_v1(doc, unit_id=93, character_id=1121)
    twice = inject_v1(once, unit_id=93, character_id=1121)

    assert get_value(twice, "PlayerUnlockedUnitTypes").count(93) == 1
    assert get_value(twice, "PlayerCharacters").count(1121) == 1
    units = get_value(twice, "PlayerUnits")
    matches = [u for u in units if u.get("unitType") == 93 and u.get("characterId") == 1121]
    assert len(matches) == 1
