# GameVault v0.9.0

## Providers, resolvers and editions
- New **Quellen & Resolver** page with live status for IGDB, PS4 catalog, ORBISPatches, PS4 update summary, local covers and library totals.
- ORBISPatches provider resolves CUSA pages and reads the latest patch through its internal `loadpatches` endpoint. It is a modular fallback because this is not a guaranteed public API.
- **Alle Resolver ausführen** runs PS4 catalog, ORBISPatches and IGDB in order and presents a trace.
- PS4 update refresh uses the update summary first and ORBISPatches as fallback.
- Resolver events are cached per game (last 30 events).

## Collection editions
Games now support region, media format, edition, storefront, tags and notes. The add-game dialog and full editor expose these fields.

## Operations
- JSON library export endpoint: `/api/export/games.json`.
- Existing local covers, IGDB, updates, duplicate exclusions and responsive UI remain.
