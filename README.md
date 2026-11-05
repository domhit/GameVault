# GameVault v0.6.1

## Metadata editor and resolver UX
- Full metadata editor modal for title, identifier type, TitleID/serial, IGDB ID, publisher, developer, genre, release date, value and description.
- Manual TitleID/serial input is normalized and persisted.
- Direct numeric IGDB ID assignment supported from the editor and IGDB search dialog.
- IGDB search is now a real result dialog with cover previews, match confidence and explicit **Übernehmen** actions.
- `ID / IGDB auflösen` now displays a trace: identifier, PS4 CUSA resolution, IGDB search, best match and application result.
- Busy spinners are shown for editor save, IGDB search/accept and ID resolver operations.
- Existing PostgreSQL database is migrated automatically. No re-import required.

Keep `IGDB_CLIENT_ID` and `IGDB_CLIENT_SECRET` configured in Portainer.
