# GameVault Backlog

## v1.6 - Active development

- Frontend startup: keep the entire library eagerly loaded and fully rendered. No pagination, no batch append and no scroll-triggered fetching. dev1 adds a staged startup loader and parallel initial data requests. dev3 adds a precomputed full-library read cache that is invalidated by database commits and rebuilt immediately in a debounced background task.

## Resolver quality

- Research and implement authoritative Title-ID -> canonical-name resolvers comparable to SerialStation for **Xbox Classic / Xbox 360**.
- Research equivalent canonical-name resolution for **Nintendo Wii / Wii U / Nintendo 3DS** and later Nintendo Switch.
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


### v1.6.0-dev5
- Fix startup regression in dev3 by importing SQLAlchemy `event`, required by the library-cache `after_commit` listener.


#### v1.6.0-dev5
- Make the full-library cache fail-safe: cache build failures can never return an empty library.
- Reuse the proven direct library serializer for both cache snapshots and direct fallback.
- Validate cache item count against PostgreSQL before publishing a snapshot; log and expose rebuild errors.
- Serve the last good cache while a new generation rebuilds, and use `DIRECT-FALLBACK` on cold/broken caches.
