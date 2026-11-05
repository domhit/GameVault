# GameVault v0.5.0

## IGDB Metadata Resolver
- Bulk enrichment for PS2, PS3, PS4 and Xbox 360.
- Uses platform-filtered IGDB searches.
- Exact/high-confidence matches at 94% or better are applied automatically.
- Lower-confidence matches are marked `review` and can be inspected/accepted in the UI.
- Enriches description, developer, publisher, genres, release date and cover.
- Existing values are preserved. Confirmed IGDB matches are locked against automatic replacement.
- Data-quality API: `/api/metadata/quality`.
- Existing cover cascade and PS4 package import remain available.

## Portainer configuration
Create a Twitch developer application and set these stack environment variables without committing them to Git:

```text
IGDB_CLIENT_ID=<Twitch application client ID>
IGDB_CLIENT_SECRET=<Twitch application client secret>
```

The compose passes them into GameVault. Restart/recreate the container, then use **IGDB aktualisieren**.

## Safety
GameVault never downloads game packages. IGDB images are cached in `/volume1/docker/gamevault/data/covers`. Existing PostgreSQL data is migrated automatically.
