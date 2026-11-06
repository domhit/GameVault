# GameVault v0.7.0

## UI & metadata quality
- Mobile-safe custom dialogs replace native browser alert/confirm/prompt flows in primary actions.
- Responsive header, editor and dialog layout for phone/tablet.
- Metadata quality uses critical vs optional fields instead of an all-or-nothing flag.
- Field cards expose state by color: red critical missing, yellow optional missing, orange manual/protected, blue provider/IGDB populated.
- Full metadata editor includes IGDB ID, identifiers, catalog fields, extended IGDB fields, collection fields, PriceCharting URL and manual cover URL.
- Manual remote cover URLs are downloaded into `/data/covers`; the UI remains local-cover-only.
- PriceCharting URL from Game Collector import is visible on the detail page.
- `BACKLOG.md` records cross-platform game grouping and modded-console installed-game inventory.
