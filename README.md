# GameVault v1.4.0

GameVault v1.5 development starts from the stable v1.4.0 release. GameVault is a self-hosted game collection, backup inventory and console-inventory application built with FastAPI and PostgreSQL for Docker/Portainer deployments.

## Highlights

- Visual multi-platform game library with covers, search, filters and responsive desktop/mobile UI.
- IGDB metadata, cover, rating and platform-specific release-date enrichment.
- Original-platform detection from IGDB release history with a 365-day launch window for simultaneous platform releases.
- Cross-Platform view groups titles that share a confirmed IGDB identity on at least two different platforms; platform buttons open the exact edition.
- Physical ownership is independent from installation/backup state and can distinguish Disc and Cartridge/Module.
- Manual library entry for Nintendo 64, Super Nintendo and Game Boy, including IGDB lookup and physical/digital formats.
- Filtered IGDB refreshes update only the current library selection and filters remain active during metadata cleanup.

## Supported console inventory

| Platform | Inventory source |
| --- | --- |
| PlayStation 3 | CFW FTP + webMAN MOD + Sony MMS history |
| PlayStation Vita | VitaShell FTP (`ur0:/shell/db/app.db` + `PARAM.SFO`) |
| PlayStation 4 | GoldHEN FTP (`app.db` / `addcont.db`) |
| Xbox 360 | Aurora (`content.db` / `settings.db`) |
| Xbox Classic | XBMC4Gamers (`MyPrograms6.db`) |
| Wii U | [GameVault Wii U Exporter](https://github.com/domhit/GameVault-WiiU-Exporter) |
| Wii / vWii | USB Loader GX data exported through the GameVault Wii U Exporter |
| Nintendo 3DS | [GameVault Nintendo 3DS Exporter](https://github.com/domhit/GameVault-Nintendo-3DS-Exporter) |

Console providers are read-only. GameVault does not intentionally modify console databases, installed games, save data or update files.

## Manual / offline platforms

Nintendo 64, Super Nintendo and Game Boy games can be added manually. A game can independently record:

- the platform/edition represented by the entry;
- physical ownership (`Disc` or `Cartridge`);
- media such as Cartridge, ROM, Virtual Console or Digital;
- IGDB metadata and original/platform release dates.

## Nintendo exporters

### Nintendo 3DS

Install and run the [GameVault Nintendo 3DS Exporter](https://github.com/domhit/GameVault-Nintendo-3DS-Exporter), then expose its `installed_titles.json` through your normal 3DS FTP server. GameVault imports games, updates and DLC while ignoring system/TWL content and known homebrew management utilities.

### Wii U / Wii / vWii

The [GameVault Wii U Exporter](https://github.com/domhit/GameVault-WiiU-Exporter) provides the Wii U inventory JSON and can export the Wii/vWii USB Loader GX inventory used by GameVault.

## Docker / GHCR

The GitHub Actions workflow publishes container images to `ghcr.io/domhit/gamevault`:

- `main` -> `latest`
- version tags (`v*`) -> matching version image
- development branch -> `dev`

For Portainer, use `docker-compose.yml` and configure at least `POSTGRES_PASSWORD`. See `.env.example` for the available environment variables.

## Metadata and data sources

IGDB is the primary external metadata provider. Platform-specific sources are retained separately so console-scanned facts such as identifiers, installed versions, storage locations and history are not silently replaced by external metadata.

See `THIRD_PARTY_SOURCES.md` for external providers and attribution details.

## Backups and package import

GameVault can track backup/package inventory independently from the console-installed state. See `PACKAGE_IMPORT.md` for the current package import format and workflow.

## Roadmap

The active backlog is maintained in `BACKLOG.md`. Upcoming areas include PlayStation Vita inventory, Nintendo Switch inventory when test hardware is available, Wii U/vWii installed-size detection, backup/restore improvements and additional technical hardening.

## License

See `LICENSE`.
