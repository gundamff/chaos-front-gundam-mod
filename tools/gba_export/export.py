"""Best-effort GBA ROM analysis and asset export with placeholder fallback."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from tools.gba_export.placeholders import generate

SEARCH_NEEDLES: tuple[tuple[str, str], ...] = (
    ("utf-8", "RX-78"),
    ("utf-8", "阿姆罗"),
    ("ascii", "RX-78"),
    ("ascii", "AMURO"),
    ("gbk", "阿姆罗"),
    ("utf-16-le", "RX-78"),
    ("utf-16-le", "阿姆罗"),
)

RESEARCH_BUDGET_S = 30.0


@dataclass
class RomAnalysis:
    path: str
    size: int
    title: str
    string_hits: dict[str, int | None] = field(default_factory=dict)
    dump_attempted: bool = False
    dump_succeeded: bool = False
    dump_reason: str = ""


@dataclass
class ExportResult:
    used_placeholders: bool
    assets_dir: Path
    rom_path: Path | None
    analysis: RomAnalysis | None
    offsets_path: Path | None = None


def find_rom(rom_arg: str | None, repo: Path) -> Path | None:
    if rom_arg:
        candidate = Path(rom_arg)
        if candidate.is_file():
            return candidate
        if "*" in rom_arg:
            matches = sorted(Path(repo / rom_arg).parent.glob(Path(rom_arg).name))
            if not matches:
                matches = sorted(repo.glob(rom_arg))
            return matches[0] if matches else None
        return candidate if candidate.exists() else None

    rom_dir = repo / "rom"
    if not rom_dir.is_dir():
        return None
    matches = sorted(rom_dir.glob("*.gba"))
    return matches[0] if matches else None


def _search_strings(data: bytes) -> dict[str, int | None]:
    hits: dict[str, int | None] = {}
    for encoding, text in SEARCH_NEEDLES:
        key = f"{encoding}:{text}"
        try:
            needle = text.encode(encoding)
        except UnicodeEncodeError:
            hits[key] = None
            continue
        idx = data.find(needle)
        hits[key] = idx if idx >= 0 else None
    return hits


def analyze_rom(rom_path: Path) -> RomAnalysis:
    data = rom_path.read_bytes()
    title = data[0xA0:0xAC].split(b"\x00", 1)[0].decode("ascii", errors="replace")
    return RomAnalysis(
        path=str(rom_path),
        size=len(data),
        title=title,
        string_hits=_search_strings(data),
    )


def attempt_structured_dump(
    rom_path: Path,
    raw_dir: Path,
    analysis: RomAnalysis,
    *,
    budget_s: float = RESEARCH_BUDGET_S,
) -> tuple[bool, str, Path | None]:
    """Quick research spike; v1 stops at string/offset discovery."""
    started = time.monotonic()
    analysis.dump_attempted = True

    if analysis.size != 32 * 1024 * 1024:
        return False, f"unexpected ROM size {analysis.size}", None

    if not any(v is not None for v in analysis.string_hits.values()):
        elapsed = time.monotonic() - started
        if elapsed > budget_s:
            return False, "research budget exceeded before string hits", None
        return (
            False,
            "no known CN/ASCII markers (RX-78, 阿姆罗); sprite offsets not mapped",
            None,
        )

    raw_dir.mkdir(parents=True, exist_ok=True)
    offsets_path = raw_dir / "gba_offsets.json"
    offsets = {
        "rom": str(rom_path),
        "string_hits": analysis.string_hits,
        "sprites": {},
        "note": "partial — string hits only; tile/sprite dump not implemented",
    }
    offsets_path.write_text(json.dumps(offsets, indent=2) + "\n", encoding="utf-8")
    return False, "string hits recorded but sprite/tile dump not available for v1", offsets_path


def run_export(
    *,
    rom_arg: str | None,
    assets_dir: Path,
    raw_dir: Path,
    repo: Path,
) -> ExportResult:
    rom_path = find_rom(rom_arg, repo)
    analysis: RomAnalysis | None = None
    offsets_path: Path | None = None

    if rom_path is not None:
        analysis = analyze_rom(rom_path)
        dump_ok, reason, offsets_path = attempt_structured_dump(
            rom_path, raw_dir, analysis
        )
        analysis.dump_succeeded = dump_ok
        analysis.dump_reason = reason
        if dump_ok:
            generate(assets_dir)
            return ExportResult(
                used_placeholders=False,
                assets_dir=assets_dir,
                rom_path=rom_path,
                analysis=analysis,
                offsets_path=offsets_path,
            )

    generate(assets_dir)
    return ExportResult(
        used_placeholders=True,
        assets_dir=assets_dir,
        rom_path=rom_path,
        analysis=analysis,
        offsets_path=offsets_path,
    )


def write_status_note(path: Path, result: ExportResult) -> None:
    lines = ["# GBA export status (v1)", ""]
    if result.analysis is None:
        lines.append("- **ROM:** not found under `rom/*.gba`")
    else:
        a = result.analysis
        lines.extend(
            [
                f"- **ROM:** `{Path(a.path).name}` ({a.size:,} bytes, title `{a.title}`)",
                f"- **CN string hits:** "
                + (
                    "none for RX-78 / 阿姆罗 (utf-8, gbk, utf-16-le, ascii)"
                    if not any(v is not None for v in a.string_hits.values())
                    else str({k: hex(v) for k, v in a.string_hits.items() if v is not None})
                ),
                f"- **Structured dump:** {'yes' if a.dump_succeeded else 'no'} — {a.dump_reason}",
            ]
        )
    lines.extend(
        [
            f"- **Assets:** {'placeholders' if result.used_placeholders else 'from ROM dump'} → `{result.assets_dir}`",
            "- **Next:** map RX-78 map/portrait tile regions (custom charset likely); until then CF patch uses labeled PNGs.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def analysis_dict(result: ExportResult) -> dict:
    payload = {
        "used_placeholders": result.used_placeholders,
        "assets_dir": str(result.assets_dir),
        "rom_path": str(result.rom_path) if result.rom_path else None,
        "offsets_path": str(result.offsets_path) if result.offsets_path else None,
    }
    if result.analysis is not None:
        payload["analysis"] = asdict(result.analysis)
    return payload
