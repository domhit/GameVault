# GameVault v0.4.0

Self-hosted game collection, backup catalog and metadata monitor.

## Highlights
- Bulk metadata refresh with PostgreSQL persistence.
- PS4 TitleID backfill from linked packages.
- PS4 title enrichment from the SerialStation-derived open dataset.
- PS4 latest-known update comparison from the Sony update summary dataset. GameVault never downloads PKG files.
- Xbox 360 metadata and artwork through x360db.
- PS2 and PS3 serial-based community cover lookup, downloaded once to `/data/covers`.
- Platform badges and colors: PS4 blue, PS3 red, PS2 gold, Xbox 360 green.
- Update status filters and counters.
- Existing v0.2 PostgreSQL database is migrated automatically.

## Deployment
The compose is prepared for Synology paths `/volume1/docker/gamevault/postgres` and `/volume1/docker/gamevault/data`. Set `POSTGRES_PASSWORD` in Portainer. After deployment click **Metadaten aktualisieren**. The first bulk run may take several minutes.

## Data sources
See `THIRD_PARTY_SOURCES.md`. Availability and completeness depend on upstream projects. No game/update packages are downloaded.
