# Chaos Front Gundam Mod

Personal, local-use tooling to append Gundam units and pilots to *Chaos Front* via patched `resources.assets` and save injection.

**Not for public redistribution.** Do not commit ROMs, GBA dumps, or game binaries to this repository (`rom/`, `raw/`, `*.gba` are gitignored).

## Setup

```bash
pip install -r requirements.txt
pytest
```

## v1 workflow (RX-78-2 + 阿姆罗)

Place a GBA ROM under `rom/*.gba` (optional; placeholders are generated if export fails).

```bash
pip install -r requirements.txt
python -m tools.gba_export --out assets
python -m tools.cf_patch --tables-only --game "F:\SteamLibrary\steamapps\common\Chaos Front" --patch patches/v1-rx78.yaml
python -m tools.save_inject --save "%USERPROFILE%\AppData\LocalLow\ChaosGalaxyStudio\Chaos Front\savedata0.cf"
python -m tools.verify_tables --patched --patch patches/v1-rx78.yaml --game "F:\SteamLibrary\steamapps\common\Chaos Front"
python -m tools.cf_patch --restore backups\<timestamp>
```

Adjust `--game` and `--save` paths for your install. After patching, note the backup folder printed as `Backup: backups\<timestamp>`; it also contains `patch-meta.json` for verification.

Save injection creates `<save>.bak` by default before atomically replacing the save. Use `--no-backup` only when you deliberately do not want that safety copy. To restore, close the game and rename the `.bak` file over the modified save (for example, rename `savedata0.cf.bak` to `savedata0.cf`).

### Known limitation: texture injection (v1)

**Do not run `python -m tools.cf_patch` without `--tables-only` for v1.** The default path attempts Texture2D injection after table patching; UnityPy cannot add or clone Texture2D objects through a supported API, so the tool **ABORTS** and leaves the original `resources.assets` in place (backup is still created).

v1 table patching uses **`--tables-only`**, which updates `UnitTypeData`, `CharacterData`, and `LanguageData` only. Map-unit and portrait PNGs under `assets/` are prepared for a future writer; in-game sprites may still show clone-source art until texture injection is unblocked.

Automated table verification:

```bash
python -m tools.verify_tables --baseline --game "F:\SteamLibrary\steamapps\common\Chaos Front"
python -m tools.verify_tables --patched --patch patches/v1-rx78.yaml --meta backups\<timestamp>\patch-meta.json
```

`cf_patch` writes `patch-meta.json` into its printed backup directory after a successful patch. If it is absent, `--patch` alone is enough; language indices are read from live unit 93 / character 1121 rows.

Manual acceptance checklist: [docs/acceptance-v1.md](docs/acceptance-v1.md).

## BepInEx runtime plugin (preferred for next steps)

Community mods use BepInEx DLLs ([Snrasha plugins](https://snrasha.github.io/chaosfront/plugins.html)). This repo now has a Mono plugin skeleton:

- Source: [`plugins/CfGundamMod/`](plugins/CfGundamMod/)
- Docs: [`plugins/README.md`](plugins/README.md)
- Build: `dotnet build -c Release` from that folder (auto-deploys to game `BepInEx\plugins`)

**v0.2** runtime-clones unit 93 (RX-78-2) + character 1121 (阿姆罗), unlocks on load/new game. See `plugins/README.md`. Texture swap is 0.3.

Portrait candidate from Genesis Character Icons: `assets/portrait-170.png` (Amuro).

## Deferred (same pipeline, not v1)

- **Ships** (`kind=1`): append via the same YAML `clone_from` pattern once v1 is accepted; no separate architecture.
- **Texture visual smoke**: offline UnityPy path still blocked; prefer BepInEx runtime texture swap once probes are done.

## Design

See [docs/superpowers/specs/2026-09-29-chaos-front-gundam-mod-design.md](docs/superpowers/specs/2026-09-29-chaos-front-gundam-mod-design.md) for scope, v1 success criteria, and architecture.


https://www.spriters-resource.com/nintendo_switch/sdgundamggenerationgenesis/