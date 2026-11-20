# GameVault Backlog

## Active development

- **v1.5 / PlayStation Vita** on persistent branch `develop`: real-hardware discovery first. Identify authoritative installed-title data, Title ID/Content ID, versions, DLC/update relationships, storage and installed sizes before choosing FTP-only integration or a dedicated exporter.

## Console inventory

- **PlayStation Vita CFW**: native Vita inventory provider implemented in dev2 from `app.db` + App/Patch/DLC `PARAM.SFO`; next validate real-hardware scan results, then add sizes and evaluate PSP/PS1/RetroArch as separate inventory streams.
- **Nintendo Switch / Atmosphere**: deferred until the test console is available again. Follow the same real-hardware-first provider approach.
- Determine reliable installed-size data for **Wii U** titles and **Wii/vWii** content without expensive full directory walks where possible.
- Investigate reliable Xbox 360 DLC inventory and active/disabled Title Update state.
- Optional `ps3netsrv`/NAS mapping so `/netX` PS3 games can obtain sizes from the NAS.

## Library and metadata

- Extend manual/offline platform support beyond Nintendo 64, SNES and Game Boy where useful.
- Saved filters and tag manager / bulk tagging.
- Continue improving platform-specific/original release handling for unusual ports, remasters and Virtual Console/inject edge cases when real examples appear.
- Restore/extend remote update availability where authoritative public sources exist.

## Backup and operations

- Backup/restore bundle for PostgreSQL dump, covers, JSON/CSV exports and non-secret configuration.
- Credential encryption / secret-store strategy; console credentials are currently stored in PostgreSQL.
- Background/cancellable console size scans if synchronous scans become too slow.
- Content-change detection to avoid recalculating unchanged folder sizes.

## Historical / research

- Further PS3 MMS field/type decoding and optional SaveData/trophy historical-footprint support without conflating SaveData timestamps with Last Played.
- Console timezone property and canonical UTC normalization for providers that expose local wall-clock timestamps, especially Aurora history.
