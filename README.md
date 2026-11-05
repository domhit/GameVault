# GameVault v0.6.5

## Endpoint hotfix
The v0.6.4 frontend referenced two routes that had been lost during the v0.6 merge. Both are restored and validated:

- `PUT /api/games/{game_id}/metadata` for the full metadata editor.
- `POST /api/games/{game_id}/igdb-direct/{igdb_id}` for direct IGDB assignment and the **Übernehmen** action.

Manual IGDB assignment uses `force=True`, so a deliberate user action overrides `metadata_locked`; unattended bulk enrichment still respects locks. Manual TitleID/Serial values are preserved.

The local-cover policy from v0.6.4 remains unchanged: UI covers are served only from `/covers/...`, physically stored under `/volume1/docker/gamevault/data/covers`.
