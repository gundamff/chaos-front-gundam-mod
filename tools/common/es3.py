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
