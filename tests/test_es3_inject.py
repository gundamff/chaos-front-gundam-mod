import json
from pathlib import Path

import pytest

from tools.common.es3 import get_value, parse_es3, stringify_es3
from tools.save_inject.__main__ import inject_save
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


def test_inject_v1_rejects_mismatched_character_and_exp_lengths():
    doc = _load_fixture()
    get_value(doc, "PlayerCharacterEXPs").pop()

    with pytest.raises(
        ValueError,
        match="PlayerCharacters and PlayerCharacterEXPs lengths differ",
    ):
        inject_v1(doc)


def test_inject_save_creates_backup_by_default_and_atomically_replaces(
    tmp_path, monkeypatch
):
    save_path = tmp_path / "savedata0.cf"
    original = FIXTURE.read_text(encoding="utf-8")
    save_path.write_text(original, encoding="utf-8")
    replacements = []
    real_replace = __import__("os").replace

    def replace(source, destination):
        source = Path(source)
        destination = Path(destination)
        assert source.parent == destination.parent
        assert source != destination
        replacements.append((source, destination))
        real_replace(source, destination)

    monkeypatch.setattr("tools.save_inject.__main__.os.replace", replace)

    inject_save(save_path)

    assert Path(str(save_path) + ".bak").read_text(encoding="utf-8") == original
    assert replacements and replacements[-1][1] == save_path
    assert 1121 in get_value(parse_es3(save_path.read_text(encoding="utf-8")), "PlayerCharacters")


def test_inject_save_can_opt_out_of_backup(tmp_path):
    save_path = tmp_path / "savedata0.cf"
    save_path.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")

    inject_save(save_path, backup=False)

    assert not Path(str(save_path) + ".bak").exists()


def test_inject_save_does_not_mutate_or_backup_invalid_save(tmp_path):
    save_path = tmp_path / "savedata0.cf"
    doc = _load_fixture()
    get_value(doc, "PlayerCharacterEXPs").pop()
    original = json.dumps(doc)
    save_path.write_text(original, encoding="utf-8")

    with pytest.raises(ValueError, match="lengths differ"):
        inject_save(save_path)

    assert save_path.read_text(encoding="utf-8") == original
    assert not Path(str(save_path) + ".bak").exists()
