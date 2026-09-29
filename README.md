# Chaos Front Gundam Mod

Personal, local-use tooling to append Gundam units and pilots to *Chaos Front* via patched `resources.assets` and save injection.

**Not for public redistribution.** Do not commit ROMs, GBA dumps, or game binaries to this repository (`rom/`, `raw/`, `*.gba` are gitignored).

## Setup

```bash
pip install -r requirements.txt
pytest
```

CLI commands will be documented here as they land in later tasks.

## Design

See [docs/superpowers/specs/2026-09-29-chaos-front-gundam-mod-design.md](docs/superpowers/specs/2026-09-29-chaos-front-gundam-mod-design.md) for scope, v1 success criteria, and architecture.
