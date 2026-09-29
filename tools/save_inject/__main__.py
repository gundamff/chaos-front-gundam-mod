from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from pathlib import Path

from tools.common.es3 import parse_es3, stringify_es3
from tools.save_inject.inject import inject_v1


def inject_save(
    save_path: Path,
    *,
    unit_id: int = 93,
    character_id: int = 1121,
    backup: bool = True,
) -> None:
    save_path = Path(save_path)
    text = save_path.read_text(encoding="utf-8")
    doc = parse_es3(text)
    out = inject_v1(doc, unit_id=unit_id, character_id=character_id)
    rendered = stringify_es3(out)

    if backup:
        shutil.copy2(save_path, Path(str(save_path) + ".bak"))

    fd, temp_name = tempfile.mkstemp(
        prefix=f".{save_path.name}.", suffix=".tmp", dir=save_path.parent
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(rendered)
        os.replace(temp_path, save_path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Inject unit/character into an ES3 save file")
    parser.add_argument("--save", required=True, type=Path, help="Path to save file")
    parser.add_argument(
        "--backup",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Write a .bak copy before modifying (default: enabled)",
    )
    parser.add_argument("--unit", type=int, default=93, help="Unit type id to inject")
    parser.add_argument("--character", type=int, default=1121, help="Character id to inject")
    args = parser.parse_args(argv)

    inject_save(
        args.save,
        unit_id=args.unit,
        character_id=args.character,
        backup=args.backup,
    )


if __name__ == "__main__":
    main()
