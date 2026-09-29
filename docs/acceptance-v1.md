# v1 acceptance checklist (RX-78-2 + 阿姆罗)

Matches design §1 success criteria. Run after `cf_patch --tables-only`, `save_inject`, and optionally `verify_tables`.

## Automated (offline)

- [ ] `python -m tools.verify_tables --patched --patch patches/v1-rx78.yaml` — unit count ≥ 93, character 1121, CN strings for RX-78-2 / 阿姆罗
- [ ] `python -m tools.cf_patch --restore backups\<timestamp>` then `verify_tables --baseline` — no unit 93 / character 1121

## Manual (in-game)

1. **Launch & regression** — Game starts without errors; original units (e.g. ID 1–92) still appear and behave normally.
2. **Roster after save inject** — After `save_inject`, formation screen shows **RX-78-2** name and **阿姆罗** name; portrait may still be clone-source art until texture injection is unblocked.
3. **Map & combat** — Unit 93 can deploy to map and enter battle without crash (balance not in scope).
4. **Factory purchase** — With unlock path active, factory can buy unit 93 (verify manually; minimal gate fixes only if blocked).
5. **Restore** — `cf_patch --restore` returns `resources.assets` to pre-patch state; game runs as before patch.

## Not in v1 / blocked

- **Ships** — Deferred; same `clone_from` YAML pipeline when scheduled; not part of this vertical slice.
- **Texture visual smoke** — **Blocked.** Default `cf_patch` (without `--tables-only`) aborts on Texture2D injection. v1 uses table-only patch; do **not** sign off on custom map-unit or portrait visuals until a safe writer lands.

## Notes

- Table patch command: `python -m tools.cf_patch --tables-only --game <install> --patch patches/v1-rx78.yaml`
- Save path (typical): `%USERPROFILE%\AppData\LocalLow\ChaosGalaxyStudio\Chaos Front\savedata0.cf`
