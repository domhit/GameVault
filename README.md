# GameVault v0.8.0

## Add games directly
The library no longer depends on Game Collector/XML for new titles. Use **+ Spiel** in the header, enter title, platform and optionally TitleID/Serial, then enrich via IGDB or edit metadata manually. Existing XML/XLSX imports remain available for bulk import.

## PS4 update availability
- **PS4 Updates** refreshes latest-known PS4 update metadata by CUSA using the existing update-summary provider.
- GameVault compares that version against the highest archived Package whose category is Patch/Update.
- Statuses: `Aktuell`, `Update verfügbar`, `Unbekannt`.
- List filter: **Update verfügbar**.
- Detail view shows local patch, online-current version and status.
- Information only. GameVault does not download PKG files.

All v0.7.4 duplicate exclusions/comparison, metadata quality, local cover handling and responsive dialogs remain.
