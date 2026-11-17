# GameVault v1.3 development

Current build: **v1.3.0-dev7**  
Branch: **develop-v1.3**  
Container channel: **ghcr.io/domhit/gamevault:dev**

## Baseline

v1.3 starts from the validated v1.2.0 stable release. PS3, PS4, Xbox 360 and Xbox Classic behavior must remain regression-compatible while Nintendo providers are added.

## Nintendo targets

1. Nintendo Switch / Atmosphere
2. Wii U with CFW/homebrew access
3. Nintendo 3DS with CFW/homebrew access

For each platform, identify authoritative installed-title databases/manifests before adding directory-crawl fallbacks. Reuse the existing `ConsoleProvider` / `InstalledGame` model, separate inventory from history/enrichment sources, preserve manual mappings across rescans, and expose source-row/deduplication diagnostics.

## dev1

- Version line moved to `1.3.0-dev1`.
- GitHub Actions dev branch configured for `develop-v1.3`.
- `:dev` container tag follows `develop-v1.3`.
- Documentation moved from release-candidate wording to active v1.3 development wording.
- No Nintendo provider has been introduced yet.


### dev2
- Adds Wii U / GameVault Exporter as the first Nintendo console provider.
- Reads `/fs/vol/external01/wiiu/apps/GameVault-WiiU-Exporter/installed_titles.json` read-only over FTP.
- Imports GAME parents and attaches UPDATE/DLC rows using canonical Wii U base Title IDs.
- Preserves USB/NAND source rows and exporter metadata in scan diagnostics.
- Adds Wii U to IGDB platform resolution and the console-management UI.


### dev3
- Fixes Wii U GAME/UPDATE/DLC parent diagnostics so children with a source parent are no longer reported as orphans before the parent is matched into the GameVault library.
- Normalizes Wii U line breaks and search-only trademark symbols for IGDB matching.
- Stores IGDB's original `first_release_date` separately from the earliest release date for the selected platform (for example Wii U Virtual Console).


### dev4
- Actually applies IGDB search-title normalization (line breaks, ®/™, punctuation aliases).
- IGDB refresh of already linked games now loads `release_dates` with the game's current platform, so `platform_release_date` is populated retroactively.
- Exposes original and platform-specific release dates in the normal game UI/edit flow where release fields are rendered.


### dev5
- Fixes the IGDB manual-search HTTP 500 by importing `re` for the search normalizer.
- Accepts both scalar and expanded-object `release_dates.platform` values when mapping platform releases.
- Displays Original-Release and platform-specific release in the normal game detail view.
- Existing IGDB bindings are refreshed with the current GameVault platform so platform release dates can be backfilled.


#### dev6
- Adds Nintendo Wii as a separate GameVault platform through the public GameVault Wii U Exporter v0.2.0 `wii_usbloadergx.json`.
- Uses USB Loader GX `WII.cache` as the current installed-game inventory source: six-character Wii Game ID, cached title and exact `usb1:/wbfs/...` path.
- Carries USB Loader GX PlayCount into GameVault history when provided.
- Adds Wii / IGDB platform mapping and console-management UI support.
- Keeps Wii U and Wii inventory as separate providers even when both JSON files are exposed through the same Wii U FTP server.


#### dev7
- Improves Wii metadata titles for known poor USB Loader GX cache names using stable Wii Game IDs.
- Reads `GXGameStatistics.cfg` directly over FTP as a fallback when the exporter JSON contains no PlayCount values.
- Marks known Wii ROM hacks/mods as manual-metadata candidates instead of automatically mapping them to the retail parent game during bulk IGDB refresh.
- Preserves original cache titles in `history_raw_json` for diagnostics.
