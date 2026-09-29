from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools.common.paths import repo_root
from tools.gba_export.export import run_export, write_status_note


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export GBA ROM assets into assets/ (placeholder fallback for v1)."
    )
    parser.add_argument(
        "--rom",
        help="ROM path or glob (default: rom/*.gba under repo root)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output assets directory (default: <repo>/assets)",
    )
    parser.add_argument(
        "--raw",
        type=Path,
        default=None,
        help="Raw dump directory (default: <repo>/raw)",
    )
    parser.add_argument(
        "--status-note",
        type=Path,
        default=None,
        help="Write brief findings markdown (default: docs/superpowers/notes/gba-export-status.md)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable result summary on stdout",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    root = repo_root()
    assets_dir = args.out or (root / "assets")
    raw_dir = args.raw or (root / "raw")
    status_path = args.status_note or (
        root / "docs" / "superpowers" / "notes" / "gba-export-status.md"
    )

    result = run_export(
        rom_arg=args.rom,
        assets_dir=assets_dir,
        raw_dir=raw_dir,
        repo=root,
    )
    write_status_note(status_path, result)

    if args.json:
        from tools.gba_export.export import analysis_dict

        print(json.dumps(analysis_dict(result), indent=2))
    else:
        if result.rom_path:
            print(f"ROM: {result.rom_path}")
        else:
            print("ROM: (none found)")
        print(f"Assets: {result.assets_dir}")
        print(f"Status note: {status_path}")

    if result.used_placeholders:
        print("USING_PLACEHOLDERS=1", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
