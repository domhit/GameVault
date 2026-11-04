# GameVault 0.2.0

Self-hosted game collection and PS4 backup archive with PostgreSQL.

## Changes in 0.2.0
- Desktop UI redesigned around two independently scrolling panes.
- Game details always open at the top without losing the left library scroll position.
- Shows TitleID, current value, publisher, developer, genre, release date, collection status, completeness and completion state.
- Shows Game Collector cover URLs when they are reachable; local Game Collector paths remain placeholders until the cover importer is implemented.
- Shows missing-metadata status and filter.
- PS4 XLSX import writes the normalized CUSA TitleID back to a matched Game Collector PS4 record.
- More robust cleanup of package names for Game/Update/Patch/DLC matching.
- Synology compose paths use `/volume1/docker/gamevault`.

## Portainer
Set `POSTGRES_PASSWORD` in the stack environment, deploy `docker-compose.yml`, then open port 8080.
