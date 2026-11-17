# GameVault v1.3.0-dev4

GameVault is a self-hosted game collection, backup inventory and console-inventory application. It runs as a FastAPI web application with PostgreSQL persistence and is designed for Docker/Portainer deployments.

## v1.3.0 development

v1.3.0-dev4 starts the Nintendo console-inventory development line on top of the validated v1.2.0 Sony + Xbox baseline. Existing supported console providers remain:

- PlayStation 3 / CFW + webMAN MOD
- PlayStation 4 / GoldHEN
- Xbox 360 / Aurora
- Xbox Classic / XBMC4Gamers

Current v1.3 development targets Nintendo Switch / Atmosphere, Wii U CFW and Nintendo 3DS CFW. dev1 only establishes the new development/version/workflow baseline; dev2 introduces the Wii U / GameVault Exporter provider. Nintendo Switch and Nintendo 3DS providers follow in later builds.

## User interface

- Full-width responsive game wall on desktop.
- Two-column portrait layout on phones.
- Full-screen mobile game details with Previous / selection / Next navigation.
- Search/filter bar remains sticky while scrolling.
- Detail page restores the previous library scroll position when closed.
- Secondary dialogs always open above the full-screen detail page.
- Enter triggers the natural primary action in login/search/ID/editor dialogs where unambiguous.
- Human-readable German date display (`dd.mm.yyyy hh:mm:ss`) while APIs/database keep structured timestamps.
- IGDB user and critic ratings including vote/review counts.

## Console inventory

### PlayStation 3

Sources are deliberately separate and merged by TitleID/serial:

1. **webMAN MOD** confirms currently playable PS3 disc/folder/network content, including ps3netsrv `/netX/...` titles.
2. **FTP** provides local `/dev_hdd0/PS3ISO`, `/dev_hdd0/GAMES`, `/dev_hdd0/game`, PARAM.SFO, local paths and local size scanning.
3. **MMS (`/dev_hdd0/mms/db/metadata_db_hdd`)** enriches matching titles with Game Data, installed patch, required firmware and play-history information.

Specific FTP content types remain intact when the same title is also exposed by webMAN. Local PS3 ISOs therefore stay `PS3 ISO`; installed HG/PS1/PS2 content stays its native category; webMAN-only `/netX` content remains `webMAN Game`.

#### PS3 MMS history

The proprietary MMS database is decoded from `metadata_db_hdd`, `metadata_db_hdd.idx` and `md_schema.scm`.

Validated RTC layout for `Common.stat.timeLastUsed`:

- year: 2-byte big endian
- month
- day
- reserved byte
- UTC hour
- minute
- second

Executable installed titles (PSN/Classics) use `playCount > 0` plus `Common.stat.timeLastUsed` for Last Played.

Disc/ISO titles use their matching Game Data/update record. Controlled tests with **HAZE (BLUS30094)** and **The Evil Within (BLES01916)** confirmed:

- `gameCategory = 6000`, `bootable = 0` identifies Game Data/update records.
- `_GDATA_...` is a Game Data record.
- `_INST_...` is an installed/update record.
- `Game.version` is the base version.
- `Game.param1` contains the installed patch version in the validated samples (HAZE `01.36`; The Evil Within `01.05`).
- `Game.ps3SystemVer` contains the required PS3 firmware when present.
- repeated pure ISO starts update `Common.timeModified`; this is used as the Disc/ISO Last Played/activity value.
- `Game.timeModified` remains diagnostic because historical records showed values consistent with broader MMS maintenance operations.
- no synthetic Disc/ISO play count is generated.

MMS Game Data never creates a playable parent by itself. It enriches a parent discovered through webMAN/FTP. Historical Game Data without a currently playable parent remains non-playable.

### PlayStation 4 / GoldHEN

- Reads `/system_data/priv/mms/app.db` and `addcont.db` through FTP (default GoldHEN port 2121).
- Installed game filter is based on CUSA + `uiCategory=game` + category `gd/gp` + `/user/appmeta/`.
- Reads local game version, storage and DLC.
- `lastAccessTime` is treated as Last Played, normalized as UTC, then rendered in the browser's local timezone.
- PS4 update availability remains available through the existing online resolver path.

### Xbox 360 / Aurora

- Reads Aurora `content.db` and `settings.db` through FTP.
- Supports Xbox 360 games, XBLA, Xbox Classic entries and Title Updates.
- Collapses multi-disc/source duplicates while retaining diagnostic counts.
- `UserRecentGames.ContentId -> ContentItems.Id -> TitleId` maps recent-history events to GameVault.
- Aurora `DateTime` is decoded from Windows FILETIME.
- The current implementation preserves the already validated Aurora wall-clock value in the UI without a second browser timezone conversion.
- Unmapped historical ContentIds are reported, never guessed.
- Orphan Title Updates are reported separately from unknown games.

### Xbox Classic / XBMC4Gamers

- Reads the configured `MyPrograms6.db` through FTP.
- Uses TitleID, title, path and size from the database.
- `iTimesPlayed` is the play count.
- `last_played` is Last Played.
- `lastAccessed` is retained separately and is not substituted for Last Played.
- Duplicate source rows sharing one TitleID are reported and collapsed.

## Play-history semantics

GameVault uses **successful launch/start** as the common meaning of “played”; it does not claim active playtime.

| Platform/source | Last Played | Play count |
|---|---|---|
| PS3 installed/PSN/Classics | MMS `timeLastUsed`, confirmed by `playCount > 0` | MMS `playCount` |
| PS3 Disc/ISO | matching GD/INST `Common.timeModified` | unavailable |
| PS4 | `app.db.lastAccessTime` | unavailable |
| Xbox 360 | Aurora `UserRecentGames.DateTime` | unavailable |
| Xbox Classic | XBMC4Gamers `last_played` | `iTimesPlayed` |

## Console scan diagnostics

Diagnostics are intended to explain every reduction from source rows to canonical GameVault items.

PS3 MMS reports physical records separately from alias lookup keys:

- `records_decoded`
- `unique_record_title_ids`
- `inventory_matched_records`
- `inventory_unmatched_records`
- `aggregate_lookup_keys`
- `alias_keys`
- `game_data_titles`
- `updated_titles`

Xbox 360 reports source/unique/merged parent and TU rows, RecentGames mapped/unmapped counts, and orphan child content. Xbox Classic reports raw DB rows, game rows, unique TitleIDs and merged duplicate rows. PS4 reports games/DLC and exact ignored-row reasons.

## Metadata and library features

- Game Collector XML import.
- Specialized PS4 Package XLSX import (see `PACKAGE_IMPORT.md`).
- IGDB resolver, direct IGDB-ID assignment and bulk refresh.
- IGDB user/critic ratings and counts.
- Local cover caching/provider cascade.
- Metadata editor with per-field manual-source protection.
- Duplicate analysis, exclusions and merge.
- Console-created games and manual matching/unmatching.
- JSON library export.
- Admin/visitor mode.
- Persistent per-console manual matching across rescans.
- Local console size scans with cached results; PS3 `/netX` entries are deliberately skipped by PS3 FTP sizing.

## Configuration

See `.env.example`. Important settings include PostgreSQL connection, IGDB client credentials, admin password/session duration and cookie security.

Console credentials are currently stored in PostgreSQL. Prefer anonymous/read-only FTP or dedicated low-privilege credentials where the console/CFW supports them.

## Docker image channels

The included GitHub Actions workflow currently builds:

- `main` -> `ghcr.io/domhit/gamevault:latest`
- `develop-v1.3` -> `ghcr.io/domhit/gamevault:dev`
- `v*` tags -> matching version tag

v1.3 development now runs on `develop-v1.3`; `main` remains the stable release line.

## Known limitations

- PS3 Disc/ISO MMS activity is a best validated launch/activity signal from controlled tests, not an official Sony API.
- PS3 Disc/ISO launch count is unavailable and is not synthesized.
- PS3 network ISO size is not measurable through PS3 FTP; webMAN/ps3netsrv still provides availability.
- Aurora RecentGames can retain ContentIds no longer present in the current `content.db`; those events stay unmapped.
- Console credentials are not encrypted at rest in the current release candidate.
- Nintendo Switch, Wii U and Nintendo 3DS providers are the v1.3 development target and are not implemented in dev1 yet.


#### Wii U / GameVault Exporter
- Reads the exporter JSON read-only through Wii U FTP.
- Default path: `/fs/vol/external01/wiiu/apps/GameVault-WiiU-Exporter/installed_titles.json`.
- Base games become Wii U parent inventory rows; updates and DLC are retained as child content.
- Wii U Title IDs are normalized to the `00050000...` base identifier for matching.
- Publisher, region, Product Code and exporter diagnostics remain available as source metadata.


#### Wii U dev3 refinements
- Wii U child inventories remain attached to their canonical `00050000...` parent identifiers without false orphan warnings.
- IGDB title search ignores line breaks plus ®/™ markers while preserving display titles.
- `release_date` is the original game release; `platform_release_date` is the earliest IGDB release for the current GameVault platform.
