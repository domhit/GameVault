# GameVault v0.6.0

- Metadata editor for title, TitleID/serial, publisher and developer.
- Per-game ID to title to IGDB resolver; PS4 CUSA is resolved before IGDB search.
- Identifier types: CUSA (PS4), SERIAL (PS2/PS3), TITLEID (Xbox 360).
- Extended IGDB fields: game modes, perspectives, themes, franchises, engines and multiplayer modes.
- Filters for missing cover, missing identifier, local multiplayer and local co-op.
- PS4 duplicate detection at `/api/duplicates` and package-preserving merge endpoint.
- Manual edits are locked against bulk automatic overwrites.
- Existing PostgreSQL data migrates automatically; existing cover/import functionality remains.
