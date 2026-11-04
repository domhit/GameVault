# GameVault v0.4.1

## Cover-Provider-Kaskade
- PS4: CUSA lookup in Dinos17/FPKGi-Catalog-Hub; only `cover_url` is consumed, never PKG links.
- PS3: multiMAN Resources first, st-alves PS3 Covers as fallback. Serial variants with hyphen, underscore and compact form are tried.
- PS2: xlenore/ps2-covers with normalized serial variants.
- Covers are cached under `/volume1/docker/gamevault/data/covers`.
- Existing covers are replaced only when the cascade finds a valid image larger than 1 KB.
- Per-game provider, check timestamp and last error are stored in PostgreSQL.

Deploy through GitHub Actions/GHCR as before. After recreation in Portainer, select **Cover aktualisieren**. Existing PostgreSQL data is migrated automatically.

## v0.4.1 hotfix
- Fixes `/api/games` 500 caused by missing SQLAlchemy `Game` mappings for `cover_provider`, `cover_checked_at`, and `cover_error`.

## v0.4.2 UI hotfix
- Local cached covers under `/covers/...` are now rendered instead of being rejected by the old HTTP-only image check.
- Restores platform accents: PS4 blue, PS3 red, PS2 gold, Xbox 360 green.
- Keeps the independent library/detail scrolling behavior from v0.2.
