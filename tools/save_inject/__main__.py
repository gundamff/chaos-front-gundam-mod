from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from tools.common.es3 import parse_es3, stringify_es3
from tools.save_inject.inject import inject_v1


def main() -> None:
    parser = argparse.ArgumentParser(description="Inject unit/character into an ES3 save file")
    parser.add_argument("--save", required=True, type=Path, help="Path to save file")
    parser.add_argument("--backup", action="store_true", help="Write a .bak copy before modifying")
    parser.add_argument("--unit", type=int, default=93, help="Unit type id to inject")
    parser.add_argument("--character", type=int, default=1121, help="Character id to inject")
    args = parser.parse_args()

    text = args.save.read_text(encoding="utf-8")
    if args.backup:
        shutil.copy2(args.save, Path(str(args.save) + ".bak"))
    doc = parse_es3(text)
    out = inject_v1(doc, unit_id=args.unit, character_id=args.character)
    args.save.write_text(stringify_es3(out), encoding="utf-8")


if __name__ == "__main__":
    main()
