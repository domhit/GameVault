# GameVault Backlog - v1.3 development

## Stable baseline

v1.2.0 is the validated Sony + Xbox stable baseline on `main`. v1.3 work happens on `develop-v1.3`.

## v1.3 - Nintendo console inventory

Active branch: `develop-v1.3`.

Target environments:
- Nintendo Switch / Atmosphere (deferred: test console currently unavailable)
- Wii U CFW/jailbreak
- Nintendo 3DS CFW

First principle: identify authoritative installed-title databases/manifests before directory crawling. Reuse the common ConsoleProvider + InstalledGame model, manual matching, history-source separation and diagnostic pattern established in v1.2.0.

## Future console and offline-library support

- Sony PlayStation Vita CFW inventory over the network; first investigate authoritative installed-title metadata before implementing a provider.
- Nintendo Switch / Atmosphere inventory remains planned but deferred until the console is available for real-device testing.
- Add manual game-entry workflows for consoles without a practical network inventory path, initially Nintendo 64, Super Nintendo (SNES) and Game Boy. These should integrate with the same IGDB metadata, cover and collection model without pretending to be console-scanned installations.

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
