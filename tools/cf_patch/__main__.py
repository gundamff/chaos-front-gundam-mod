from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

import UnityPy
import yaml

from tools.cf_patch.backup import backup_resources, restore_backup
from tools.cf_patch.table_patch import apply_v1_tables
from tools.cf_patch.textures import inject_textures
from tools.cf_patch.unity_text import (
    TextAssetDiscoveryError,
    read_text_asset,
    write_text_asset,
)
from tools.common import xml_tables as xt
from tools.common.paths import default_game_root, repo_root, resources_assets


_TABLE_NAMES = ("UnitTypeData", "CharacterData", "LanguageData")


def patch_tables(
    game_root: Path,
    patch_path: Path,
    backups_dir: Path,
    *,
    inject_texture_assets: bool = False,
) -> tuple[Path, dict]:
    game_root = Path(game_root)
    assets_path = resources_assets(game_root)
    if not assets_path.is_file():
        raise FileNotFoundError(f"resources.assets not found: {assets_path}")

    patch = yaml.safe_load(Path(patch_path).read_text(encoding="utf-8"))
    temp_dir = None
    source_stream = assets_path.open("rb")
    try:
        env = UnityPy.load(source_stream)
        source_xml = {name: read_text_asset(env, name) for name in _TABLE_NAMES}

        unit_id = int(patch["unit"]["id"])
        units = xt.parse_items(source_xml["UnitTypeData"])
        unit_indexes = {item.get("Index") for item in units}
        if "93" in unit_indexes:
            raise RuntimeError("UnitTypeData Index 93 already exists; aborting")
        if str(unit_id) in unit_indexes:
            raise RuntimeError(f"UnitTypeData Index {unit_id} already exists; aborting")

        unit_xml, char_xml, lang_xml, meta = apply_v1_tables(
            source_xml["UnitTypeData"],
            source_xml["CharacterData"],
            source_xml["LanguageData"],
            patch,
        )

        backup_dir = backup_resources(game_root, Path(backups_dir))
        temp_dir = Path(
            tempfile.mkdtemp(prefix=".cf-patch-", dir=assets_path.parent)
        )
        if inject_texture_assets:
            root = repo_root()
            manifest = json.loads(
                (root / "assets/manifest.json").read_text(encoding="utf-8")
            )
            meta["textures"] = inject_textures(env, manifest, root)
        write_text_asset(env, "UnitTypeData", unit_xml)
        write_text_asset(env, "CharacterData", char_xml)
        write_text_asset(env, "LanguageData", lang_xml)
        env.save(out_path=str(temp_dir))
    except BaseException:
        if temp_dir is not None:
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise
    finally:
        source_stream.close()

    try:
        staged_assets = Path(temp_dir) / assets_path.name
        if not staged_assets.is_file():
            raise RuntimeError(
                f"UnityPy did not produce staged {assets_path.name}; "
                f"original preserved, backup at {backup_dir}"
            )
        os.replace(staged_assets, assets_path)
    finally:
        if temp_dir is not None:
            shutil.rmtree(temp_dir, ignore_errors=True)

    return backup_dir, meta


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Patch or restore Chaos Front resources.assets data tables."
    )
    parser.add_argument("--game", type=Path, default=default_game_root())
    parser.add_argument("--patch", type=Path)
    parser.add_argument("--restore", type=Path)
    parser.add_argument(
        "--tables-only",
        action="store_true",
        help="Patch only UnitTypeData, CharacterData, and LanguageData.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)

    if args.restore is not None:
        if args.patch is not None:
            parser.error("--restore cannot be combined with --patch")
        restore_backup(args.restore, args.game)
        print(f"Restored resources from {args.restore} to {args.game}")
        return 0

    if args.patch is None:
        parser.error("--patch is required unless --restore is used")

    try:
        backup_dir, meta = patch_tables(
            args.game,
            args.patch,
            repo_root() / "backups",
            inject_texture_assets=not args.tables_only,
        )
    except TextAssetDiscoveryError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(f"ABORTED: {exc}", file=sys.stderr)
        return 2

    print(f"Backup: {backup_dir}")
    print(
        f"Patched UnitTypeData Index {meta['unit_id']} and "
        f"CharacterData Index {meta['character_id']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
