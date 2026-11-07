# GameVault v1.2.0-dev4

## Manual console-to-library matching
- Unknown Xbox 360 and PS3 inventory entries now offer **Vorhandenes Spiel suchen**.
- Search is restricted to the correct platform and supports title or TitleID/Serial substrings.
- The search dialog can hide games already linked to console inventory.
- Manual matching links the installed row and copies a missing Xbox TitleID or PS3 Serial with `console_scan` provenance.
- The confirmation dialog is platform-aware and no longer mentions PS3 for Xbox matches.

## Inventory review filters
- Installed content defaults to **Unbekannt**.
- Status filters: Unbekannt, Alle, Zugeordnet.
- Type filter is generated from the scanned inventory, including Xbox 360 Game, XBLA, Xbox Classic and Title Update.
- Live counters show all, unknown and matched entries.

## Suggestions
- Automatic suggestions also consider safe title containment, so `DiRT` can suggest `ColinMcRae: Dirt`.
- Containment is suggestion-only and never triggers automatic assignment.
