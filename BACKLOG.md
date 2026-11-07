# GameVault Backlog

## Cross-platform library model
- Group the same game across platforms into one logical game entry.
- Show every owned platform/version on the combined game page.
- Preserve platform-specific identifiers, packages, installed status and metadata beneath the shared game identity.

## Console installation inventory
Read which games are installed on the user's modded consoles. Implement per-console adapters because access methods differ by platform/CFW.

Known environment to investigate in a later release:
- Xbox 360: Aurora
- PlayStation 3: Rebug
- PlayStation 4: GoldHEN
- Nintendo Switch: Atmosphere
- Wii U: jailbreak/CFW
- PlayStation 2: FreeHDBoot
- Xbox Classic: PrometheOS + XBMC4Gamers
- Nintendo 3DS: jailbreak/CFW

Target state in GameVault: owned, backup available/location, installed console(s), installed version where obtainable, latest known update, completion and multiplayer metadata.

## Priority B - Update availability
- Restore the PS4 `Update verfügbar` feature.
- Resolve latest known PS4 update by CUSA (Sony/OrbisPatches-compatible metadata source).
- Compare latest remote version with the highest archived Patch/Update package in GameVault.
- Statuses: `Aktuell`, `Update verfügbar`, `Unbekannt`.
- Add list filter and detail badge.
- Information only: never download game/update PKG files.

## Implemented in v0.8.0
- Manual creation of new games from the web UI (`+ Spiel`), followed by IGDB enrichment/editor maintenance.
- PS4 update availability: refresh latest-known version by CUSA, compare with highest archived local patch, show status and filter.

## v1.0 candidates inspired by VideoGameTrackarr
- Logical game identity with platform editions.
- Saved filters and tag manager/bulk tagging.
- Backup and restore bundle: PostgreSQL dump, local covers, JSON/CSV exports, configuration without secrets.
- Console-provider adapters for installed-game inventory remain the differentiating priority after the data model is ready.


## v1.1 - Console Inventory
- Common ConsoleProvider abstraction.
- PlayStation 3 / Rebug first.
- Read-only FTP baseline with PARAM.SFO parsing.
- Optional webMAN MOD enrichment for additional ISO/JB/network paths.
- Match installed TitleID/version against GameVault.

## v1.1 dev2 validation
- Validate real Rebug FTP directory behavior and FTP server compatibility.
- Refine CATEGORY classification from real PARAM.SFO samples.
- Improve webMAN HTML/list parsing against the installed webMAN MOD version.
- Add manual match/unmatch for unknown installed titles.
- Add library filters `Auf PS3 installiert` and `Nicht auf PS3 installiert`.
- Decide on credential encryption/secret handling before stable v1.1.0.

## v1.1 dev3
- Preserve manual install matches across rescans instead of rebuilding them.
- Investigate webMAN endpoints or SFO extraction for ISO APP_VER.
- Add edit-console UI and credential protection.
- Add installed-version comparison where a reliable online PS3 update source is available.

## Console import pattern established in dev4
- Unknown console inventory can create library games.
- Platform identifier is authoritative and duplicate-protected.
- Console-created games are linked immediately and enriched through IGDB.
- Reuse this workflow for Switch, Wii U, 3DS, Aurora and later providers.

## v1.2 Aurora dev2 validation
- Validate actual Aurora installation path and content.db schema.
- Refine TitleID/title/path extraction from the real database.
- Read Aurora settings.db scan paths.
- Add x360db enrichment before IGDB.
- Evaluate installed DLC and Title Update inventory.

## v1.2 dev4
- Identify installed DLC tables/content types from further Aurora/XM360 data.
- Present Title Updates and DLC nested under their parent Xbox game.
- Add x360db enrichment before IGDB for unknown TitleIDs.
- Compare installed Aurora TU version against an online TU source where reliable.

## v1.2 dev5
- Nest Title Updates and DLC underneath the parent Xbox game in the console UI.
- Add x360db title/cover enrichment before IGDB for console-created Xbox games.
- Add bulk review actions only after manual search behavior is validated.

## v1.2 dev6
- Add real DLC provider data when a reliable Aurora/XM360 source is available.
- Improve nested child cards with MediaID, file size and active TU state.
- Add x360db enrichment for Xbox 360 and evaluate a dedicated Xbox Classic metadata source.
