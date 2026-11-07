# GameVault v1.2.0-dev3

Aurora provider mapped to the real Aurora database schema.

## Exact Aurora schema
- Reads `ContentItems` directly from `content.db`.
- Uses Aurora's `TitleId`, `TitleName`, `Directory`, `MediaId`, `BaseVersion`, `ContentGroup`, `ContentType`, `FileType`, and `ScanPathId` columns.
- `ContentGroup 1` becomes Xbox 360 Game.
- `ContentGroup 2` becomes XBLA.
- `ContentGroup 4` becomes Xbox Classic.
- `ContentGroup 5` (Homebrew/System) is ignored for library inventory.
- Multi-disc rows with the same TitleID are collapsed into one game while retaining all paths.

## Title Updates
- Reads the dedicated `TitleUpdates` table.
- Stores TitleID, MediaID, BaseVersion, TU Version, display name, file size and live/backup path where available.
- Title Updates are associated with their parent GameVault game by TitleID and do not offer `Als neues Spiel übernehmen`.

## Aurora settings
- Reads `ScanPaths` from `settings.db` for diagnostics.
- The real paths from the supplied database include Content, Homebrew, Games360 and XboxClassic.

## UI
- Console counts separate Xbox 360 Game, XBLA, Xbox Classic and Title Update.
- Added filters for available/not available on Xbox 360.
- Child content such as Title Updates is labelled separately from the main installed game.

PS3 inventory remains included.
