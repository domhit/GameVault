# Third-party sources and console data sources

## Online metadata

- IGDB API by Twitch: metadata, covers, game modes, user rating and aggregated critic rating. Requires IGDB Client ID/Secret.
- Dinos17/FPKGi-Catalog-Hub: PS4 CUSA cover URL mapping only; GameVault does not consume package download URLs.
- ORBISPatches: PS4 title/patch fallback through its public website/internal load-patches request. Unofficial and potentially unstable.
- Axekinn/ps4-scraper datasets: PS4 catalog/update-summary fallback used by online resolver helpers.
- xenia-manager/x360db: Xbox 360 metadata/cover enrichment.
- gauss77/Multiman-Resources and st-alves/ps3-covers: PS3 covers.
- xlenore/ps2-covers: PS2 covers.

Artwork and metadata remain property of their respective owners/providers.

## Read-only console sources

- PS3: FTP `PARAM.SFO`, local ISO/folder paths, webMAN MOD pages and the proprietary Sony MMS files `metadata_db_hdd`, `metadata_db_hdd.idx`, `md_schema.scm`.
- PS4: GoldHEN FTP access to Sony SQLite databases `app.db` and `addcont.db`.
- Xbox 360: Aurora SQLite databases `content.db` and `settings.db`; optional NOVA health/diagnostics.
- Xbox Classic: XBMC4Gamers `MyPrograms6.db`.

GameVault console providers are read-only scanners. The application does not intentionally modify console databases, Game Data, save data, ISOs or Title Updates.

- Nintendo 3DS: GameVault Nintendo 3DS Exporter v0.1.0 `installed_titles.json`, read-only over FTP. System title metadata remains console-derived.

- PlayStation Vita: VitaShell FTP, Sony shell `ur0:/shell/db/app.db`, and read-only game/patch/add-on `PARAM.SFO` metadata.
