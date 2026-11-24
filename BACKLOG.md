# GameVault Backlog

## v1.6 release preparation
- Duplikat-Merge preserves InstalledGame paths and saved selections on the surviving library record.
- Duplikatvergleich zeigt entscheidungsrelevante Installations-/ROM-Pfade und begrenzte Cover statt allgemeiner Metadatenfelder.
- Duplikatsuche uses indexed same-platform candidate blocks and bounded result output instead of a full all-pairs comparison.
- Final regression testing across all real console inventories, library cache, metadata refresh, covers and responsive UI before `v1.6.0-rc1`.
- Keep resolver rules and third-party attribution synchronized with implementation.

## Backup inventory and operations
- Design a platform-spanning backup inventory/scan. The existing PS4 XLSX package import stores filename, Title ID, category, version, storage location and size; equivalent source spreadsheets/inventories for Xbox and other platforms should be evaluated as structured backup sources.
- Reconcile owned library entries, console-installed inventory and backup-file inventory without conflating backup presence with installation.
- Retain the current Package size audit as a maintenance tool until the generalized backup scan replaces or absorbs it.
- Backup/restore bundle for PostgreSQL dump, covers, persistent GameTDB catalogs, exports and non-secret configuration.
- Credential encryption / secret-store strategy; console credentials are currently stored in PostgreSQL.

## Console inventory
- Nintendo Switch / Atmosphere: defer until the test console is available; keep the real-hardware-first provider approach.
- Determine reliable installed-size data for Wii U and Wii/vWii without expensive full directory walks where possible.
- Investigate Xbox 360 DLC inventory and active/disabled Title Update state.
- Optional ps3netsrv/NAS mapping so `/netX` PS3 games can obtain sizes from the NAS.
- Consider dedicated handling for Vita fan ports and PlayStation Mobile content.

## Resolver and metadata quality
- Evaluate TheGamesDB only as an optional retro fallback if it materially improves real unmatched ROMs; IGDB remains primary.
- Replace remaining explicit title overrides only where an authoritative identifier source is validated.
- Saved filters and tag manager / bulk tagging.
- Continue unusual port/remaster/original-platform rules only from real examples.
- Restore/extend remote update availability where authoritative public sources exist.
- Optional cached ROM hashes only if a hash resolver proves useful on real unmatched titles.

## Historical / research
- Further PS3 MMS field/type decoding and optional SaveData/trophy historical-footprint support without conflating timestamps with Last Played.
- Console timezone property and canonical UTC normalization for providers exposing local wall-clock timestamps, especially Aurora history.
