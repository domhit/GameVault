# GameVault 0.1.1

Self-hosted game collection and PS4 backup archive using PostgreSQL.

## GitHub / GHCR
The workflow builds `ghcr.io/domhit/gamevault:latest` from `main` and version tags from `v*` tags.

## Portainer
Create a stack from `docker-compose.yml`. Set at least `POSTGRES_PASSWORD` in the stack environment. PostgreSQL data is persistent in the named volume `gamevault_db`.

Open `http://<docker-host>:8080`, import the Game Collector XML first and the PS4 XLSX second.
