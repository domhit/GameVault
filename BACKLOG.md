# GameVault Backlog after v1.2.0

## v1.2.0 release gate

- Complete RC acceptance checklist.
- Merge validated RC to `main` and tag `v1.2.0`.
- Do not add additional console-provider scope before stable.

## v1.3 - Nintendo console inventory

Start a new Nintendo-focused development branch after v1.2.0 stable.

Target environments:
- Nintendo Switch / Atmosphere
- Wii U CFW/jailbreak
- Nintendo 3DS CFW

First principle: identify authoritative installed-title databases/manifests before directory crawling. Reuse the common ConsoleProvider + InstalledGame model, manual matching, history-source separation and diagnostic pattern established in v1.2.0.

## Post-v1.2 technical improvements

- Console timezone property and canonical UTC normalization for every provider, especially Aurora wall-clock history.
- Optional ps3netsrv/NAS storage mapping so `/netX` PS3 games can obtain sizes directly from the NAS.
- Credential encryption/secret-store strategy; current console credentials are stored in PostgreSQL.
- Background/cancellable console size scans if synchronous scans become too slow.
- Content-change detection to avoid recalculating unchanged folder sizes.
- Further PS3 MMS field/type decoding and optional SaveData/trophy historical-footprint support without conflating SaveData timestamps with Last Played.
- Investigate reliable Xbox 360 DLC source and active/disabled TU state.
- Restore/extend remote update availability where authoritative public sources exist.

## Cross-platform library model

- Group the same game across platforms into one logical game identity while preserving platform editions, identifiers, packages, console installations and metadata.
- Saved filters and tag manager/bulk tagging.
- Backup/restore bundle for PostgreSQL dump, covers, JSON/CSV exports and non-secret configuration.
