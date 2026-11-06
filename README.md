# GameVault

GameVault is a self-hosted game collection and backup inventory for Docker. It combines collection metadata with technical package information, local cover storage, metadata enrichment, resolver diagnostics and PS4 update tracking.

**Current stable release: v1.0.0**

## Highlights

- Responsive web UI for desktop, tablet and phone
- PostgreSQL persistence
- Docker / Docker Compose deployment
- GitHub Actions builds published to `ghcr.io/domhit/gamevault`
- PlayStation 2, PlayStation 3, PlayStation 4 and Xbox 360 library support
- Manual game creation and editing
- Game Collector XML import
- Documented PS4 Package XLSX import
- Local cover cache under `/data/covers`
- IGDB metadata enrichment
- PS4 CUSA resolver chain and ORBISPatches fallback
- PS4 update availability tracking
- Backup packages for Game, Patch and DLC
- Effective local PS4 version from the highest Game/Patch package version
- Manual package correction
- Metadata quality view
- Duplicate detection, comparison, merge and persistent `Kein Duplikat` exclusions
- Region, format, edition, storefront, tags and notes
- PriceCharting links imported from Game Collector
- Provider / resolver diagnostics
- JSON library export

## Architecture

```text
Browser
  |
GameVault / FastAPI
  |-- IGDB metadata
  |-- PS4 catalog / resolver
  |-- ORBISPatches
  |-- PS4 update metadata
  |-- cover providers
  |
PostgreSQL + /data/covers
```

The application is deliberately metadata/read-only toward external game sources. It does not download game or update PKG files.

## Docker deployment

The included `docker-compose.yml` is prepared for the current Synology layout:

```text
/volume1/docker/gamevault/postgres
/volume1/docker/gamevault/data
```

Before deployment, replace `DEIN_SICHERES_PASSWORT` in both PostgreSQL locations with the same strong password. Do not commit your real password to a public repository.

For IGDB, configure these variables in Portainer rather than committing secrets:

```text
IGDB_CLIENT_ID=...
IGDB_CLIENT_SECRET=...
```

The application listens on port `8080`.

## GitHub / GHCR

Pushes to `main` build `ghcr.io/domhit/gamevault:latest`. Tags matching `v*` also create a versioned container tag through the included GitHub Actions workflow.

## Data model

### Games
A game stores collection and metadata fields such as title, platform, TitleID/Serial, IGDB relationship, publisher, developer, genres, release, value, completion state, region, format, edition, tags and notes.

### Packages
PS4 backups are separate rows related to a game:

- `Game`: Base-game backup
- `Patch`: Update/Patch backup
- `DLC`: Add-on backup

There is one internal package `version` field:

- Game version comes from the package-version source during XLSX import.
- Patch version comes from the patch/app-version source.
- DLC has no meaningful version.

For PS4 update comparison, the effective local version is the highest known version among Game and Patch packages.

## Imports

### Game Collector XML
Use the XML export from Game Collector for a structured bulk library import. Existing entries are updated on re-import.

### PS4 package XLSX
The XLSX importer is intentionally a specialized package-inventory importer, not a generic spreadsheet library importer. See [PACKAGE_IMPORT.md](PACKAGE_IMPORT.md).

The UI also exposes a downloadable XLSX template.

## Metadata & resolvers

### IGDB
IGDB is the primary general metadata source for title information, cover art, developer/publisher, genres, game modes, perspectives, themes, franchises, engines and multiplayer information.

### PlayStation 4
The PS4 resolver chain can use:

1. existing GameVault title/CUSA information
2. PS4/SerialStation-derived catalog data
3. ORBISPatches as additional CUSA/title and patch fallback
4. IGDB for general metadata

The **Quellen & Resolver** view reports provider status.

## Covers

All displayed covers are local. Remote provider images are downloaded into:

```text
/volume1/docker/gamevault/data/covers
```

Legacy Game Collector image paths are not used for display.

## PS4 update tracking

GameVault compares the latest-known online PS4 version against the highest local Game/Patch version and reports:

- `Aktuell`
- `Update verfügbar`
- `Unbekannt`

No PKGs are downloaded.

## Data quality & duplicate cleanup

The data quality view distinguishes critical and optional missing metadata. Field coloring indicates missing, manual and provider-sourced data.

Duplicate review supports:

- side-by-side details
- merge with package preservation
- permanent `Kein Duplikat` exclusions

## Export

Current JSON export:

```text
/api/export/games.json
```

## v1.1 roadmap

The next development line introduces **Console Inventory** via a common `ConsoleProvider` architecture.

First target: PlayStation 3 / Rebug

- read-only FTP as the reliable baseline
- `PARAM.SFO` parsing
- TitleID / Serial
- title
- installed `APP_VER`
- content category
- install path
- optional webMAN MOD enrichment for ISO/JB/network content
- matching installed content to the GameVault library

Later adapters are planned for PS4/GoldHEN, Xbox 360/Aurora, Nintendo Switch/Atmosphere, Wii U, PS2/FreeHDBoot, Xbox Classic/PrometheOS + XBMC4Gamers and Nintendo 3DS.

See [BACKLOG.md](BACKLOG.md) for further ideas.

## Third-party data

See [THIRD_PARTY_SOURCES.md](THIRD_PARTY_SOURCES.md). External metadata and artwork remain subject to their respective providers' terms.
