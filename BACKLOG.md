# GameVault Backlog

## v1.6 - Active development

- Frontend startup: keep the entire library eagerly loaded and fully rendered. No pagination, no batch append and no scroll-triggered fetching. dev1 adds a staged startup loader and parallel initial data requests. dev3 adds a precomputed full-library read cache that is invalidated by database commits and rebuilt immediately in a debounced background task.

## Resolver quality

- Validate and refine the new **Xbox Classic / Xbox 360** resolver coverage against the real collection; investigate unmatched IDs and regional edge cases.
- Validate the new **Wii / GameTDB** resolver against the real collection; then research equivalent canonical-name resolution for **Wii U / Nintendo 3DS** and later Nintendo Switch.
- Evaluate **TheGamesDB** as an optional retro resolver, especially platform-constrained name lookup and ROM-hash resolution, while keeping IGDB as the primary metadata store.
- Replace remaining platform-specific title overrides with maintainable resolver data where an authoritative source exists.

## Console inventory

- **Nintendo Switch / Atmosphere**: deferred until the test console is available again; use the same real-hardware-first provider approach.
- Determine reliable installed-size data for **Wii U** titles and **Wii/vWii** content without expensive full directory walks where possible.
- Investigate reliable Xbox 360 DLC inventory and active/disabled Title Update state.
- Optional `ps3netsrv`/NAS mapping so `/netX` PS3 games can obtain sizes from the NAS.
- Consider dedicated import handling for Vita fan ports and PlayStation Mobile entries currently preserved as classified special content.

## Library and metadata

- Saved filters and tag manager / bulk tagging.
- Continue improving unusual port/remaster/original-platform edge cases only from real examples.
- Restore/extend remote update availability where authoritative public sources exist.
- Optional cached ROM hashes for RetroArch if a resolver such as TheGamesDB proves materially better on real unmatched titles.

## Backup and operations

- Backup/restore bundle for PostgreSQL dump, covers, JSON/CSV exports and non-secret configuration.
- Credential encryption / secret-store strategy; console credentials are currently stored in PostgreSQL.
- Background/cancellable console size scans if synchronous scans become too slow.
- Content-change detection to avoid recalculating unchanged folder sizes.

## Historical / research

- Further PS3 MMS field/type decoding and optional SaveData/trophy historical-footprint support without conflating SaveData timestamps with Last Played.
- Console timezone property and canonical UTC normalization for providers that expose local wall-clock timestamps, especially Aurora history.


### v1.6.0-dev8
- Fix startup regression in dev3 by importing SQLAlchemy `event`, required by the library-cache `after_commit` listener.


#### v1.6.0-dev8
- Fix cache/direct HTTP 500: use existing `installed_dict()` and the proven `serial(g)` package output; remove nonexistent serializer calls.
- Never return an empty array on cache failure; direct PostgreSQL fallback remains authoritative.
- Validate snapshot count against PostgreSQL and expose concrete errors in logs/status.


#### v1.6.0-dev8
- Add Xbox 360 Title-ID resolution through cached x360db data.
- Add Xbox Classic Title-ID resolution through MobCat Xbox IDs, including regional multi-row handling.
- Feed canonical Xbox names into the existing IGDB pipeline without overwriting console-native titles.
- Add bulk Xbox resolver diagnostics, provider status, resolver trace integration and documentation.


#### v1.6.0-dev8
- Add cached GameTDB Wii Game-ID resolver before IGDB while preserving exporter-native titles and existing overrides as fallback.
- Add Wii bulk resolver diagnostics and provider status.
- Suspend expensive library-cache rebuilds during high-commit batch operations and rebuild once at batch completion.
