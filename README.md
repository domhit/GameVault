# GameVault v1.6.0-dev15

GameVault is a self-hosted game collection, backup inventory and console-inventory application built with FastAPI and PostgreSQL for Docker/Portainer deployments.

## Highlights

- Precomputed full-library read cache is rebuilt after database mutations so normal frontend starts do not repeatedly serialize the entire library.

- Visual multi-platform game library with covers, search, filters and responsive desktop/mobile UI.
- IGDB metadata, covers, ratings and platform-specific release dates.
- Original-platform detection from IGDB release history with a 365-day launch window for simultaneous releases.
- Cross-Platform view groups confirmed IGDB identities across multiple consoles while keeping every platform edition separate.
- Physical ownership is independent from installation/backup state and distinguishes Disc and Cartridge/Module.
- Filtered IGDB refreshes update only the current library selection and retain active filters.
- SerialStation resolves PlayStation Title IDs to canonical names before IGDB lookup.

## Supported console inventory

| Platform | Inventory source |
| --- | --- |
| PlayStation 3 | CFW FTP + webMAN MOD + Sony MMS history |
| PlayStation 4 | GoldHEN FTP (`app.db` / `addcont.db`) |
| PlayStation Vita | VitaShell FTP (`ur0:/shell/db/app.db` + `PARAM.SFO`) |
| Xbox 360 | Aurora (`content.db` / `settings.db`) |
| Xbox Classic | XBMC4Gamers (`MyPrograms6.db`) |
| Wii U | [GameVault Wii U Exporter](https://github.com/domhit/GameVault-WiiU-Exporter) |
| Wii / vWii | USB Loader GX data exported through the GameVault Wii U Exporter |
| Nintendo 3DS | [GameVault Nintendo 3DS Exporter](https://github.com/domhit/GameVault-Nintendo-3DS-Exporter) |

Console providers are read-only. GameVault does not intentionally modify console databases, installed games, save data or update files.

## PlayStation Vita

v1.5 adds native PS Vita inventory from VitaShell FTP and the Vita shell database.

- native games from `ux0:/app/<TITLE_ID>`;
- title updates from `ux0:/patch/<TITLE_ID>`;
- DLC from `ux0:/addcont/<TITLE_ID>`;
- Title ID, Content ID, installed version and `PARAM.SFO` metadata;
- installed-size scanning for base games, patches and DLC;
- PS1 Classics hosted through PSPemu from non-empty `ux0:/pspemu/PSP/GAME/<TITLE_ID>` directories;
- filtering of tested Vita system applications and utility/homebrew IDs without discarding known playable fan ports or PlayStation Mobile content classes.

PlayStation metadata resolution uses **SerialStation -> IGDB** when a supported PlayStation Title ID is available. See `MATCHING_RULES.md` for the tested classification and fallback rules.

## RetroArch library

v1.5 can discover and import RetroArch ROM libraries stored on the PS Vita under `ux0:/data/retroarch/roms` for:

- Game Boy
- Game Boy Color
- Game Boy Advance
- Nintendo Entertainment System
- Super Nintendo

The folder determines the platform. ROM filenames are normalized into one Game record per platform + title, while individual region/revision/language ROM files remain separate installed variants. Unexpected extensions are skipped and reported.

Retro IGDB matching includes conservative No-Intro-style title variants and keeps uncertain matches in review rather than lowering the global confidence threshold blindly.

## Manual / offline library

Games can be added manually for platforms without a console inventory provider. Physical ownership, Disc/Cartridge media, ROM/digital availability and external metadata remain independent properties.

## Nintendo exporters

### Nintendo 3DS

Install and run the [GameVault Nintendo 3DS Exporter](https://github.com/domhit/GameVault-Nintendo-3DS-Exporter), then expose its `installed_titles.json` through the normal 3DS FTP server.

### Wii U / Wii / vWii

The [GameVault Wii U Exporter](https://github.com/domhit/GameVault-WiiU-Exporter) provides the Wii U inventory and can export the Wii/vWii USB Loader GX inventory used by GameVault.

## Docker / GHCR

The GitHub Actions workflow publishes to `ghcr.io/domhit/gamevault`:

- `main` -> `latest`
- `develop` -> `dev`
- version tags (`v*`) -> matching version images

For Portainer, use `docker-compose.yml` and configure at least `POSTGRES_PASSWORD`. See `.env.example` for the available environment variables.

## Metadata and data sources

IGDB remains GameVault's primary external game-metadata provider. Platform-specific sources are retained separately so console facts such as identifiers, installed versions, paths and history are not silently overwritten.

See:

- `THIRD_PARTY_SOURCES.md` for external provider attribution;
- `MATCHING_RULES.md` for resolver order, matching heuristics and tested platform special cases;
- `PACKAGE_IMPORT.md` for package/backup import behavior;
- `BACKLOG.md` for active future work.

## License

See `LICENSE`.
