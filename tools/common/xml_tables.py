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


def insert_items(xml: str, new_items: list[dict[str, str]]) -> str:
    """Append Item rows while preserving xml declaration, MenuName wrapper, and newlines.

    Chaos Front TextAssets use:
      <?xml ...?>\\r\\n<root>\\r\\n\\t<MenuName>\\r\\n\\t\\t<Item .../>...\\r\\n\\t</MenuName>\\r\\n</root>
    Rewriting the whole document without MenuName / declaration breaks the in-game UI.
    """
    if not new_items:
        return xml

    idx = xml.rfind("</MenuName>")
    if idx < 0:
        match = re.search(
            r"</(?:UnitTypeData|CharacterData|LanguageData)>\s*\Z",
            xml,
        )
        if not match:
            raise ValueError("cannot find </MenuName> or root close for Item insert")
        idx = match.start()

    newline = "\r\n" if "\r\n" in xml else "\n"
    indent = "\t\t"
    indent_match = re.search(r"(\r?\n)([ \t]*)<Item\s", xml)
    if indent_match:
        newline = indent_match.group(1)
        indent = indent_match.group(2)

    block = "".join(f"{newline}{indent}{_render_item(it)}" for it in new_items)
    return xml[:idx] + block + xml[idx:]


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
