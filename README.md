# GameVault v1.2.0-dev15

## Console bulk import
A console can now import all still-unknown parent game entries in one operation.

- **Unbekannte übernehmen** first displays a preview with importable games, already-existing identifiers, skipped TU/DLC rows and examples.
- Import is identifier-safe: an existing platform + TitleID/Serial is linked instead of duplicated.
- New games inherit the platform identifier with `console_scan` provenance and are immediately linked to the console inventory.
- Title Updates and DLC are never created as standalone library games.
- Large console libraries deliberately skip per-title IGDB requests during bulk creation; existing global metadata/resolver actions can enrich them afterwards.

This is particularly useful for the supplied XBMC4Gamers database with more than one thousand Xbox Classic game rows.

## Provider-specific scan confirmation
The scan dialog now describes the actual provider:
- PS3: FTP + optional webMAN MOD.
- Xbox 360: Aurora `content.db` / `settings.db` over FTP, with NOVA as supplemental diagnostics.
- Xbox Classic: XBMC4Gamers `MyPrograms6.db` loaded read-only via FTP.
