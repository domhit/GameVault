# GameVault v1.2.0-dev5

## Correct wrong console assignments
- Assigned game rows now provide **Zuordnung lösen**.
- Unmatching removes the inventory link immediately.
- A TitleID/Serial copied from that console row is removed only when its metadata source is `console_scan` and it still equals the scanned identifier.
- Manually maintained identifiers are preserved.

## Xbox Classic platform
- Aurora `ContentGroup 4` is stored as platform **Xbox Classic**, not Xbox 360.
- Xbox Classic uses `TITLEID`, its own library search scope, filters and IGDB platform mapping.
- Console-created Xbox Classic titles remain linked to the physical Xbox 360 console while correctly appearing as Xbox Classic games in the library.

## Nested TU/DLC presentation
- Xbox 360 Game, XBLA and Xbox Classic entries are parent rows.
- Title Updates and future DLC rows are nested under the parent game by linked GameVault game or TitleID.
- Parent counters exclude TU/DLC; a separate child-content count is shown.
- Selecting the Title Update or DLC type still provides a direct child-only view.
- TU/DLC rows never offer `Als neues Spiel übernehmen`.
