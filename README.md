# GameVault v0.6.6

## Deterministic metadata merge
- The global `metadata_locked` flag is deprecated and no longer blocks enrichment.
- Per-field provenance is stored in `metadata_sources`.
- Manual editor changes are marked `manual` and remain protected.
- IGDB refreshes IGDB-managed fields, extended fields, multiplayer data, and local IGDB covers.
- Collection-specific fields remain untouched: TitleID/Serial, value, completion state, collection status, completeness and packages.

## Global IGDB update
The top-level **IGDB aktualisieren** action now follows the same resolver order as the detail action:
1. known IGDB ID;
2. PS4 CUSA to title resolution;
3. title plus platform IGDB search;
4. full IGDB record by ID;
5. apply standard and extended metadata.

A global busy indicator remains visible during the request. The final report includes checked, resolved by ID/title, applied, review, not found, errors and changed-field counts.
