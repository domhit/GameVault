# GameVault v1.2.0-dev6

## Delete library games safely
- Game detail now provides **Spiel löschen**.
- A preview shows packages, console links, local cover and duplicate exclusions affected.
- Deleting removes only GameVault database records and its local cached cover.
- NAS/HDD backup files and real console content are never deleted.
- Console inventory links are released so existing console content can reappear as unknown after the next scan.

## Console content in normal game details
- Xbox Title Updates and future DLC assigned to a game are now visible directly on its GameVault detail page.
- Content is grouped by physical console and shows title, MediaID/content ID, type, version, path, size and storage.
- Aurora Title Update `FileSize` is now preserved.

## Aurora DLC/TU model
- Title Updates continue to come from Aurora's dedicated `TitleUpdates` table and are nested below their parent game.
- The nested UI is DLC-ready and will display DLC as soon as a reliable source is identified; GameVault does not fabricate DLC from ambiguous `ContentItems` rows.
