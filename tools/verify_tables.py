"""Verify UnitTypeData / CharacterData / LanguageData in live resources.assets."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import UnityPy
import yaml

from tools.cf_patch.unity_text import TextAssetDiscoveryError, read_text_asset
from tools.common import xml_tables as xt
from tools.common.paths import default_game_root, resources_assets

_TABLE_NAMES = ("UnitTypeData", "CharacterData", "LanguageData")
_V1_UNIT_ID = 93
_V1_CHAR_ID = 1121


def _load_tables(assets_path: Path) -> dict[str, str]:
    if not assets_path.is_file():
        raise FileNotFoundError(f"resources.assets not found: {assets_path}")
    with assets_path.open("rb") as source:
        env = UnityPy.load(source)
        return {name: read_text_asset(env, name) for name in _TABLE_NAMES}


def _expected_cn_from_patch(patch_path: Path) -> dict[str, str]:
    patch = yaml.safe_load(patch_path.read_text(encoding="utf-8"))
    return {
        "unit_name": patch["unit"]["name_cn"],
        "unit_info": patch["unit"]["info_cn"],
        "char_name": patch["character"]["name_cn"],
        "char_info": patch["character"]["info_cn"],
    }


def _language_indices_from_meta(meta: dict) -> dict[str, int]:
    raw = meta["language_indices"]
    return {key: int(value) for key, value in raw.items()}


def _language_indices_from_tables(
    unit: dict[str, str], character: dict[str, str]
) -> dict[str, int]:
    return {
        "unit_name": int(unit["Name"]),
        "unit_info": int(unit["Info"]),
        "char_name": int(character["Name"]),
        "char_info": int(character["Info"]),
    }


def _assert_cn_strings(
    langs: list[dict[str, str]],
    indices: dict[str, int],
    expected: dict[str, str],
) -> list[str]:
    errors: list[str] = []
    for key, idx in indices.items():
        try:
            row = xt.find_item(langs, idx)
        except KeyError:
            errors.append(f"LanguageData Index={idx} ({key}) not found")
            continue
        cn = row.get("CN", "")
        want = expected[key]
        if cn != want:
            errors.append(
                f"LanguageData Index={idx} ({key}): CN={cn!r}, expected {want!r}"
            )
    return errors


def verify_baseline(tables: dict[str, str]) -> list[str]:
    errors: list[str] = []
    units = xt.parse_items(tables["UnitTypeData"])
    chars = xt.parse_items(tables["CharacterData"])

    if len(units) >= _V1_UNIT_ID:
        errors.append(
            f"baseline: expected fewer than {_V1_UNIT_ID} units, found {len(units)}"
        )
    unit_ids = {int(item["Index"]) for item in units}
    if _V1_UNIT_ID in unit_ids:
        errors.append(f"baseline: UnitTypeData Index {_V1_UNIT_ID} must not exist")

    char_ids = {int(item["Index"]) for item in chars}
    if _V1_CHAR_ID in char_ids:
        errors.append(f"baseline: CharacterData Index {_V1_CHAR_ID} must not exist")
    return errors


def verify_patched(
    tables: dict[str, str],
    *,
    meta_path: Path | None,
    patch_path: Path | None,
    require_full_count: bool = True,
) -> list[str]:
    errors: list[str] = []
    units = xt.parse_items(tables["UnitTypeData"])
    chars = xt.parse_items(tables["CharacterData"])
    langs = xt.parse_items(tables["LanguageData"])

    if require_full_count and len(units) < _V1_UNIT_ID:
        errors.append(
            f"patched: expected at least {_V1_UNIT_ID} units, found {len(units)}"
        )

    try:
        unit = xt.find_item(units, _V1_UNIT_ID)
    except KeyError:
        errors.append(f"patched: UnitTypeData Index {_V1_UNIT_ID} not found")
        unit = None

    try:
        character = xt.find_item(chars, _V1_CHAR_ID)
    except KeyError:
        errors.append(f"patched: CharacterData Index {_V1_CHAR_ID} not found")
        character = None

    if unit is None or character is None:
        return errors

    if meta_path is not None:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        indices = _language_indices_from_meta(meta)
        expected = meta.get("expected_cn")
        if expected is None:
            if patch_path is None:
                errors.append(
                    "patched: patch-meta.json has no expected_cn; pass --patch"
                )
                return errors
            expected = _expected_cn_from_patch(patch_path)
    else:
        indices = _language_indices_from_tables(unit, character)
        if patch_path is None:
            errors.append("patched: pass --patch or --meta for CN verification")
            return errors
        expected = _expected_cn_from_patch(patch_path)

    errors.extend(_assert_cn_strings(langs, indices, expected))
    return errors


def verify(
    assets_path: Path,
    *,
    baseline: bool,
    meta_path: Path | None,
    patch_path: Path | None,
    require_full_count: bool = True,
) -> list[str]:
    tables = _load_tables(assets_path)
    if baseline:
        return verify_baseline(tables)
    return verify_patched(
        tables,
        meta_path=meta_path,
        patch_path=patch_path,
        require_full_count=require_full_count,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Extract TextAsset tables from live resources.assets and verify "
            "v1 patch state (or unpatched baseline)."
        )
    )
    parser.add_argument("--game", type=Path, default=default_game_root())
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--baseline",
        action="store_true",
        help="Verify unpatched game: no unit 93 / character 1121.",
    )
    mode.add_argument(
        "--patched",
        action="store_true",
        help="Verify patched game (default when neither mode is set).",
    )
    parser.add_argument(
        "--meta",
        type=Path,
        help="backups/<timestamp>/patch-meta.json with language_indices (and optional expected_cn).",
    )
    parser.add_argument(
        "--patch",
        type=Path,
        help="Patch YAML (e.g. patches/v1-rx78.yaml) for expected CN strings.",
    )
    parser.add_argument(
        "--allow-partial-table",
        action="store_true",
        help="Skip unit-count>=93 check (fixture/snippet tables only).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    assets_path = resources_assets(args.game)

    try:
        errors = verify(
            assets_path,
            baseline=args.baseline,
            meta_path=args.meta,
            patch_path=args.patch,
            require_full_count=not args.allow_partial_table,
        )
    except (FileNotFoundError, TextAssetDiscoveryError, KeyError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1

    mode = "baseline" if args.baseline else "patched"
    print(f"OK: {mode} verification passed for {assets_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
