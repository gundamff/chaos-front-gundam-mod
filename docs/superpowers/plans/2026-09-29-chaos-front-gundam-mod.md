# Chaos Front Gundam Mod v1 Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Offline-append RX-78-2 (`unitType` 93) and Amuro (`character` 1121) into Chaos Front via `resources.assets` + ES3 save inject, using GBA-exported or placeholder art.

**Architecture:** Three file-coupled pipelines — (1) `gba_export` fills `assets/` + `manifest.json`, (2) `cf_patch` backups and mutates Unity TextAssets/Textures in place with UnityPy, (3) `save_inject` unlocks and inserts the pair into a `.cf` save. Names must append `LanguageData` rows because `UnitTypeData`/`CharacterData` store `Name`/`Info` as language indices, not raw CN strings.

**Tech Stack:** Python 3.11+, pytest, UnityPy, Pillow, PyYAML; reuse ES3 loose-JSON rules from `chaos-front-save-editor`.

## Global Constraints

- Append only — never replace unit IDs 1–92 or existing characters.
- v1 IDs: unit/model `93`, character `1121`, portrait `170`; clone combat stats from unit template `31`.
- Default game path: `F:\SteamLibrary\steamapps\common\Chaos Front`.
- ROM under `rom/` is gitignored; never commit `.gba` or full `raw/` dumps.
- Ships (`kind=1`) are out of v1 but must not paint tools into a dead-end (keep template-id driven patches).
- Every mutating tool must support backup + restore before claiming success.

---

## File Structure

| Path | Responsibility |
|------|----------------|
| `requirements.txt` | Runtime + test deps |
| `pyproject.toml` | pytest path / package root |
| `patches/v1-rx78.yaml` | Declarative clone + overrides for v1 |
| `assets/manifest.json` | Target Unity texture/sprite slot names |
| `assets/unit-93.png` / `assets/portrait-170.png` | Adapted art (placeholder OK first) |
| `tools/common/es3.py` | ES3 parse/stringify (int-key bare) |
| `tools/common/xml_tables.py` | Parse/append `<Item .../>` inside `*Data` XML |
| `tools/common/paths.py` | Resolve game/rom/backup dirs |
| `tools/cf_patch/` | Backup, TextAsset patch, texture inject, CLI |
| `tools/save_inject/` | Save unlock + unit/character insert CLI |
| `tools/gba_export/` | ROM → raw/assets (fallback: labeled placeholders) |
| `tests/` | Unit tests for xml/es3/patch builders/inject |
| `README.md` | Local-only usage + copyright boundary |

---

### Task 1: Scaffold + declarative patch

**Files:**
- Create: `requirements.txt`
- Create: `pyproject.toml`
- Create: `patches/v1-rx78.yaml`
- Create: `tools/__init__.py`
- Create: `tools/common/__init__.py`
- Create: `tools/common/paths.py`
- Create: `tests/test_paths.py`
- Create: `README.md`

**Interfaces:**
- Produces: `paths.default_game_root() -> Path`, `paths.repo_root() -> Path`, `load_patch(path) -> dict` (added in Task 2; yaml file shape fixed here)

- [ ] **Step 1: Write dependency and project files**

`requirements.txt`:
```text
UnityPy>=1.21.0
Pillow>=10.0.0
PyYAML>=6.0
pytest>=8.0.0
```

`pyproject.toml`:
```toml
[project]
name = "chaos-front-gundam-mod"
version = "0.1.0"
requires-python = ">=3.11"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

`patches/v1-rx78.yaml`:
```yaml
unit:
  id: 93
  clone_from: 31
  note: "RX-78-2"
  name_cn: "RX-78-2"
  info_cn: "地球联邦军的试作型机动战士。"
  # Icon may reuse clone until texture pipeline covers icon atlas
  reuse_icon: true
character:
  id: 1121
  clone_from: 84
  note: "阿姆罗"
  name_cn: "阿姆罗"
  info_cn: "白色恶魔。"
  portrait: 170
textures:
  map_unit: "assets/unit-93.png"
  portrait: "assets/portrait-170.png"
```

- [ ] **Step 2: Implement `tools/common/paths.py`**

```python
from __future__ import annotations

from pathlib import Path

DEFAULT_GAME = Path(r"F:\SteamLibrary\steamapps\common\Chaos Front")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_game_root() -> Path:
    return DEFAULT_GAME


def game_data_dir(game_root: Path | None = None) -> Path:
    root = game_root or default_game_root()
    return root / "Chaos Front_Data"


def resources_assets(game_root: Path | None = None) -> Path:
    return game_data_dir(game_root) / "resources.assets"
```

- [ ] **Step 3: Write failing/passing path test**

`tests/test_paths.py`:
```python
from tools.common.paths import repo_root, resources_assets


def test_repo_root_contains_patches():
    assert (repo_root() / "patches" / "v1-rx78.yaml").is_file()


def test_resources_assets_name():
    assert resources_assets().name == "resources.assets"
```

- [ ] **Step 4: Run tests**

Run: `pip install -r requirements.txt` then `pytest tests/test_paths.py -v`  
Expected: PASS (after yaml exists)

- [ ] **Step 5: Minimal README**

State: local personal use only; no ROM in git; commands will be filled as CLIs land; link to design spec.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt pyproject.toml patches/v1-rx78.yaml tools README.md tests/test_paths.py
git commit -m "chore: scaffold Python tools and v1-rx78 patch yaml"
```

---

### Task 2: XML table helpers (Language / Unit / Character)

**Files:**
- Create: `tools/common/xml_tables.py`
- Create: `tests/test_xml_tables.py`
- Create: `tests/fixtures/sample_unittype_snippet.xml`
- Create: `tests/fixtures/sample_language_snippet.xml`
- Create: `tests/fixtures/sample_character_snippet.xml`

**Interfaces:**
- Produces:
  - `parse_items(xml: str) -> list[dict[str, str]]`
  - `find_item(items, index: int) -> dict[str, str]`
  - `render_items_document(root_tag: str, items: list[dict[str, str]]) -> str`
  - `append_language(items, *, note: str, cn: str) -> tuple[list[dict[str,str]], int]`  # returns new index (1-based)
  - `clone_unit_item(template: dict, *, new_id: int, name_idx: int, info_idx: int, note: str, reuse_icon: bool) -> dict`
  - `clone_character_item(template: dict, *, new_id: int, name_idx: int, info_idx: int, note: str, portrait: int) -> dict`

**Spec note:** Real `UnitTypeData` item for id 31 looks like:

```xml
<Item Index="31" Note="异形斗兵" Name="1127" Info="1" Icon="31" Model="31" Kind="2" ... LevelType="4"/>
```

`Name`/`Info` are **LanguageData indices**. Current language table ends near Index `6058`.

- [ ] **Step 1: Add tiny fixtures** (trimmed but well-formed wrappers)

`tests/fixtures/sample_language_snippet.xml`:
```xml
<LanguageData>
<Item Index="1" Note="界面用" NoteEN="UI" EN="None" CN="无" TC="無" JP="無し" ES="Ninguno"/>
<Item Index="2" Note="x" NoteEN="x" EN="x" CN="测试" TC="測試" JP="x" ES="x"/>
</LanguageData>
```

`tests/fixtures/sample_unittype_snippet.xml`:
```xml
<UnitTypeData>
<Item Index="31" Note="异形斗兵" Name="1127" Info="1" Icon="31" Model="31" Kind="2" Type="11" Organism="1" Size="0" HP="650" EN="0" Agility="55" Limit="120" Move="4" HangarS="0" HangarL="0" Weapon1="7" Weapon2="0" Shield="0" Ablity1="16" Ablity2="0" Ablity3="0" Value="2433" Buy="4000" Sell="800" CustomCost="4000" Repair="1200" LevelType="4"/>
</UnitTypeData>
```

`tests/fixtures/sample_character_snippet.xml`:
```xml
<CharacterData>
<Item Index="84" Note="样例" Name="375" Info="509" Portrait="1" Species="0" Type="0" JoinLv="5" Shoot="22" Maneuver="21" Command="33" SP="37" Melee="10" Reaction="10" Talent1="12" Talent2="17" Talent3="12" Talent4="1" Talent5="17" Talent6="12" Talent7="1" Talent8="12" Talent9="1" Talent10="12" Skill1="1" Skill2="37" Skill3="57" SkillSpeech1="1402" SkillSpeech2="1536" SkillSpeech3="1670"/>
</CharacterData>
```

- [ ] **Step 2: Write failing tests**

```python
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
    )
    assert cloned["Index"] == "93"
    assert cloned["Model"] == "93"
    assert cloned["Name"] == "6059"
    assert cloned["Info"] == "6060"
    assert cloned["Icon"] == "31"  # reuse
    assert cloned["Weapon1"] == "7"
    assert cloned["Note"] == "RX-78-2"


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
    )
    assert cloned["Index"] == "1121"
    assert cloned["Portrait"] == "170"
    assert cloned["Name"] == "6061"
```

- [ ] **Step 3: Run tests — expect FAIL** (`ModuleNotFoundError` / missing attrs)

Run: `pytest tests/test_xml_tables.py -v`

- [ ] **Step 4: Implement `tools/common/xml_tables.py`**

```python
from __future__ import annotations

import re
from copy import deepcopy

_ITEM_RE = re.compile(r"<Item\s+([^>]+?)\/>", re.DOTALL)
_ATTR_RE = re.compile(r'([\w]+)="([^"]*)"')


def parse_items(xml: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for m in _ITEM_RE.finditer(xml):
        attrs = {am.group(1): am.group(2) for am in _ATTR_RE.finditer(m.group(1))}
        out.append(attrs)
    return out


def find_item(items: list[dict[str, str]], index: int) -> dict[str, str]:
    key = str(index)
    for it in items:
        if it.get("Index") == key:
            return it
    raise KeyError(f"Item Index={index} not found")


def _render_item(attrs: dict[str, str]) -> str:
    body = " ".join(f'{k}="{v}"' for k, v in attrs.items())
    return f"<Item {body}/>"


def render_items_document(root_tag: str, items: list[dict[str, str]]) -> str:
    inner = "".join(_render_item(it) for it in items)
    return f"<{root_tag}>{inner}</{root_tag}>"


def append_language(
    items: list[dict[str, str]], *, note: str, cn: str
) -> tuple[list[dict[str, str]], int]:
    max_idx = max((int(it["Index"]) for it in items), default=0)
    new_idx = max_idx + 1
    row = {
        "Index": str(new_idx),
        "Note": note,
        "NoteEN": note,
        "EN": cn,
        "CN": cn,
        "TC": cn,
        "JP": cn,
        "ES": cn,
    }
    return [*items, row], new_idx


def clone_unit_item(
    template: dict[str, str],
    *,
    new_id: int,
    name_idx: int,
    info_idx: int,
    note: str,
    reuse_icon: bool,
) -> dict[str, str]:
    cloned = deepcopy(template)
    cloned["Index"] = str(new_id)
    cloned["Model"] = str(new_id)
    cloned["Name"] = str(name_idx)
    cloned["Info"] = str(info_idx)
    cloned["Note"] = note
    if not reuse_icon:
        cloned["Icon"] = str(new_id)
    return cloned


def clone_character_item(
    template: dict[str, str],
    *,
    new_id: int,
    name_idx: int,
    info_idx: int,
    note: str,
    portrait: int,
) -> dict[str, str]:
    cloned = deepcopy(template)
    cloned["Index"] = str(new_id)
    cloned["Name"] = str(name_idx)
    cloned["Info"] = str(info_idx)
    cloned["Note"] = note
    cloned["Portrait"] = str(portrait)
    return cloned
```

- [ ] **Step 5: Run tests — expect PASS**

Run: `pytest tests/test_xml_tables.py -v`

- [ ] **Step 6: Commit**

```bash
git add tools/common/xml_tables.py tests/test_xml_tables.py tests/fixtures
git commit -m "feat: XML Item parse/clone helpers for Unit/Character/Language"
```

---

### Task 3: Build patched table set from real-shaped XML + yaml

**Files:**
- Create: `tools/cf_patch/table_patch.py`
- Create: `tests/test_table_patch.py`
- Modify: none

**Interfaces:**
- Consumes: `xml_tables.*`, `patches/v1-rx78.yaml`
- Produces: `apply_v1_tables(unit_xml: str, char_xml: str, lang_xml: str, patch: dict) -> tuple[str,str,str,dict]`  
  where the dict reports `{unit_id, character_id, language_indices: {...}}`

- [ ] **Step 1: Failing test** — load fixtures, apply patch dict mirroring yaml, assert unit 93 and lang growth by 4 (unit name/info + char name/info)

```python
from pathlib import Path

import yaml

from tools.cf_patch.table_patch import apply_v1_tables

FIX = Path(__file__).parent / "fixtures"


def test_apply_v1_tables_appends_four_language_rows():
    patch = yaml.safe_load((Path("patches/v1-rx78.yaml")).read_text(encoding="utf-8"))
    # fixtures only have Index 31 / 84 / lang 1-2 — remap clone targets in a local patch copy
    patch = {
        **patch,
        "unit": {**patch["unit"], "clone_from": 31},
        "character": {**patch["character"], "clone_from": 84},
    }
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
```

- [ ] **Step 2: Implement `tools/cf_patch/__init__.py` + `table_patch.py`**

```python
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
    langs, unit_info = xt.append_language(langs, note=f'{u_cfg["note"]}_info', cn=u_cfg["info_cn"])
    langs, char_name = xt.append_language(langs, note=c_cfg["note"], cn=c_cfg["name_cn"])
    langs, char_info = xt.append_language(langs, note=f'{c_cfg["note"]}_info', cn=c_cfg["info_cn"])

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
```

- [ ] **Step 3: pytest PASS**

Run: `pytest tests/test_table_patch.py -v`

- [ ] **Step 4: Commit**

```bash
git add tools/cf_patch tests/test_table_patch.py
git commit -m "feat: build appended Unit/Character/Language XML from patch yaml"
```

---

### Task 4: ES3 save inject

**Files:**
- Create: `tools/common/es3.py`
- Create: `tools/save_inject/inject.py`
- Create: `tools/save_inject/__main__.py`
- Create: `tests/test_es3_inject.py`
- Create: `tests/fixtures/minimal-save.json` (copy shape from save-editor fixture; trim OK)

**Interfaces:**
- Produces:
  - `parse_es3(text) -> dict`
  - `stringify_es3(doc) -> str`  # bare integer keys
  - `inject_v1(doc, *, unit_id=93, character_id=1121, portrait_ignored) -> dict` mutates unlocked/units/characters

- [ ] **Step 1: Port ES3 helpers** (mirror save-editor rules)

```python
# tools/common/es3.py
from __future__ import annotations

import json
import re
from typing import Any


def parse_json_loose(text: str) -> Any:
    return json.loads(re.sub(r"([{,]\s*)(\d+)(\s*:)", r'\1"\2"\3', text))


def parse_es3(text: str) -> dict[str, Any]:
    raw = parse_json_loose(text)
    doc: dict[str, Any] = {}
    for k, v in raw.items():
        if isinstance(v, dict) and "__type" in v and "value" in v:
            doc[k] = v
        else:
            doc[k] = {"value": v}
    return doc


def stringify_es3(doc: dict[str, Any]) -> str:
    return re.sub(r'([{,]\s*)"(\d+)":', r"\1\2:", json.dumps(doc, ensure_ascii=False, indent=2)) + "\n"


def get_value(doc: dict[str, Any], key: str) -> Any:
    return doc[key]["value"]


def set_value(doc: dict[str, Any], key: str, value: Any) -> None:
    doc[key]["value"] = value
```

- [ ] **Step 2: Inject logic + test**

```python
# tools/save_inject/inject.py
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
    unlocked = list(get_value(out, "PlayerUnlockedUnitTypes"))
    if unit_id not in unlocked:
        unlocked.append(unit_id)
    set_value(out, "PlayerUnlockedUnitTypes", unlocked)

    chars = list(get_value(out, "PlayerCharacters"))
    exps = list(get_value(out, "PlayerCharacterEXPs"))
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
```

Test: load `tests/fixtures/minimal-save.json`, inject, assert `93` unlocked, `1121` in characters, one unit with those ids; `stringify_es3` round-trip keeps `PlayerArmyId`.

- [ ] **Step 3: CLI `__main__.py`**

```python
# argparse: --save PATH [--backup] --unit 93 --character 1121
# read → optional *.bak → inject → write UTF-8
```

- [ ] **Step 4: pytest + commit**

```bash
pytest tests/test_es3_inject.py -v
git add tools/common/es3.py tools/save_inject tests/test_es3_inject.py tests/fixtures/minimal-save.json
git commit -m "feat: ES3 save inject for unit 93 and character 1121"
```

---

### Task 5: Placeholder assets + manifest

**Files:**
- Create: `assets/manifest.json`
- Create: `scripts/make_placeholders.py` (or `tools/gba_export/placeholders.py`)
- Create: `assets/unit-93.png`
- Create: `assets/portrait-170.png`
- Create: `tests/test_placeholders.py`

**Interfaces:**
- Produces: PNGs + manifest slots:
  - `mapUnit93` / `mapUnit93_0` (document both; inject tries known names from live game)
  - `portrait170`

- [ ] **Step 1: Generator** — Pillow create 64×64 (or match measured `mapUnit31` size during Task 6) RGB PNG with text label `RX78` / `AMURO`

- [ ] **Step 2: `assets/manifest.json`**

```json
{
  "unit_texture_candidates": ["mapUnit93", "mapUnit93_0"],
  "portrait_texture": "portrait170",
  "files": {
    "unit": "assets/unit-93.png",
    "portrait": "assets/portrait-170.png"
  }
}
```

- [ ] **Step 3: Test files exist and are non-empty PNG signatures**

- [ ] **Step 4: Commit** (binary PNGs OK if tiny)

```bash
git add assets scripts/make_placeholders.py tests/test_placeholders.py
git commit -m "feat: placeholder unit/portrait PNGs and manifest"
```

---

### Task 6: CF backup + TextAsset write via UnityPy

**Files:**
- Create: `tools/cf_patch/backup.py`
- Create: `tools/cf_patch/unity_text.py`
- Create: `tools/cf_patch/__main__.py`
- Create: `tests/test_backup.py`

**Interfaces:**
- Produces:
  - `backup_resources(game_root, backups_dir) -> Path`
  - `restore_backup(backup_dir, game_root) -> None`
  - `read_text_asset(env, name: str) -> str`
  - `write_text_asset(env, name: str, xml: str) -> None`
  - CLI: `python -m tools.cf_patch --game ... --patch patches/v1-rx78.yaml`  
    and `python -m tools.cf_patch --restore backups/<ts>`

**Implementation notes:**
- Open `resources.assets` with `UnityPy.load`.
- Find objects where `obj.type.name == "TextAsset"` and `obj.read().name` in `{UnitTypeData, CharacterData, LanguageData}` (confirm exact `.name` vs container path on first run; print inventory if missing).
- Replace `.script` / `.m_Script` bytes with UTF-8 XML from Task 3.
- `env.save()` / file overwrite **only after** backup of `resources.assets` and `resources.assets.resS` if present.
- Idempotency: if Index 93 already present, abort or no-op with message (prefer abort to avoid dup rows).

- [ ] **Step 1: Unit-test backup copy** using temp dirs (no real game required)

- [ ] **Step 2: Manual dry-run on real game** (implementer machine):

```bash
python -m tools.cf_patch --game "F:\SteamLibrary\steamapps\common\Chaos Front" --patch patches/v1-rx78.yaml --tables-only
```

Expected: backup created; UnitTypeData item count 93; LanguageData max index ≥ previous+4; `restore` brings counts back to 92 / 6058.

- [ ] **Step 3: Commit**

```bash
git add tools/cf_patch
git commit -m "feat: UnityPy TextAsset patch with backup/restore"
```

---

### Task 7: Texture / Sprite inject

**Files:**
- Create: `tools/cf_patch/textures.py`
- Modify: `tools/cf_patch/__main__.py`
- Create: `tests/test_textures_resize.py`

**Interfaces:**
- Produces: `inject_textures(env, manifest, assets_root) -> list[str]` changed object names

**Steps:**
- [ ] Inventory existing `mapUnit31` / `portrait1` (or highest portrait) via UnityPy: record width/height, format, whether Texture2D-only or Sprite+atlas.
- [ ] Resize placeholder PNG to match target dimensions (Pillow).
- [ ] Replace image data on a **cloned or newly named** Texture2D. Prefer: duplicate `mapUnit31` object metadata under name `mapUnit93` if UnityPy supports copy; else overwrite a dedicated new asset added to the file (UnityPy `Texture2D` create path — if blocked, document failure and fall back to **replacing** an unused texture only after user approval; default plan is **add/rename**, not steal live slots).
- [ ] Same for `portrait170`.
- [ ] Re-run game smoke: map/factory/portrait visible (may still be wrong palette — OK for v1 if not pink-error).

- [ ] **Commit**

```bash
git commit -am "feat: inject mapUnit93 and portrait170 textures"
```

---

### Task 8: GBA export (best-effort) wired to assets

**Files:**
- Create: `tools/gba_export/__main__.py`
- Create: `tools/gba_export/export.py`
- Create: `tools/gba_export/placeholders.py` (move from Task 5 if preferred)

**Interfaces:**
- CLI: `python -m tools.gba_export --rom rom/*.gba --out assets`
- Behavior:
  1. Locate ROM under `rom/` (glob `*.gba`).
  2. Attempt structured dump (tile/sprite research during implementation; record offsets in `raw/gga_offsets.json` if found).
  3. On failure: generate labeled placeholders into `assets/` and exit code `0` with warning `USING_PLACEHOLDERS=1` (CF pipeline must not be blocked).

- [ ] **Step 1: Implement ROM presence check + placeholder fallback**

- [ ] **Step 2: Optional research spike (same task):** search ROM for known CN string `RX-78` / `阿姆罗` to validate charset; if sprites not found in 2 hours wall time, keep placeholders and write `docs/superpowers/notes/gba-export-status.md` with findings.

- [ ] **Step 3: Commit**

```bash
git add tools/gba_export docs/superpowers/notes/gba-export-status.md
git commit -m "feat: GBA export CLI with placeholder fallback"
```

---

### Task 9: End-to-end acceptance script + README finalization

**Files:**
- Create: `tools/verify_tables.py`
- Modify: `README.md`
- Create: `docs/superpowers/plans/../` (no) — add `docs/acceptance-v1.md` checklist

**Steps:**
- [ ] `verify_tables.py` reads live `resources.assets` (binary XML extract like save-editor `extractXml`) and asserts unit count≥93, character Index 1121 exists, language indices from meta file `backups/<ts>/patch-meta.json` resolve to expected CN.
- [ ] README commands:

```text
pip install -r requirements.txt
python -m tools.gba_export --out assets
python -m tools.cf_patch --game "F:\SteamLibrary\steamapps\common\Chaos Front" --patch patches/v1-rx78.yaml
python -m tools.save_inject --save "%USERPROFILE%\AppData\LocalLow\ChaosGalaxyStudio\Chaos Front\savedata0.cf"
python -m tools.cf_patch --restore backups\<timestamp>
```

- [ ] Manual checklist in `docs/acceptance-v1.md` matching design §1 five items + ships deferred note.

- [ ] **Commit**

```bash
git add tools/verify_tables.py README.md docs/acceptance-v1.md
git commit -m "docs: v1 acceptance commands and table verifier"
```

---

## Spec coverage (self-review)

| Spec requirement | Task |
|------------------|------|
| Append unit 93 / char 1121 / portrait 170 | 2–3, 6–7 |
| Clone combat from unit 31 | 1 yaml + 2–3 |
| LanguageData indices for names | 2–3, 6 |
| Offline resources.assets patch + restore | 6 |
| GBA export with fallback | 5, 8 |
| Save unlock + inject | 4 |
| Factory unlock path | 6 tables + 4 unlock; factory buy verified manually in 9 |
| No ROM in git | Task 1 README + existing `.gitignore` |
| Ships later, same pipeline | yaml `clone_from` + kind preserved from template; documented in README/acceptance |
| Placeholder if GBA stuck | 5, 8 |

**Placeholder scan:** no TBD/TODO left in tasks. Texture “if UnityPy cannot add” has an explicit abort/approval gate, not a silent TODO.

**Type consistency:** `apply_v1_tables` / `inject_v1` / patch yaml keys (`unit.id`, `character.portrait`, `reuse_icon`) used consistently across tasks.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-29-chaos-front-gundam-mod.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — this session with executing-plans and checkpoints  

Which approach?
