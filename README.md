# GameVault v1.2.0-dev23

## PS4 installed-game filter refined
The GoldHEN `app.db` provider now treats a row as an installed PS4 game only when all of these are true:

- `titleId` matches `CUSAxxxxx`
- `uiCategory = game`
- `category` is `gd` or `gp`
- `metaDataPath` starts with `/user/appmeta/`

`contentSize` is deliberately **not** a filter. Real playable and visible titles can report `0` in that field.

This excludes the validated Destiny residual/system entries (`gdi`, `/system_ex/app/...`) without hard-coding Destiny or relying on `visible`/size heuristics.

The scan diagnostics now break ignored rows down by invalid CUSA, non-game UI category, unsupported category, metadata path, and duplicate CUSA.


### PS3 package classics and XMB/MMS diagnostics

- `/dev_hdd0/game/*/PARAM.SFO` entries with category `1P`, `2P`, `MN` and `PE` are now treated as playable installed titles.
- PS1 Classics are assigned to PlayStation 1, PS2 Classics to PlayStation 2, and PSP Minis/Remasters to PlayStation Portable while retaining the PS3 console installation.
- The PS3 scan reports files found under `/dev_hdd0/mms/db` with their sizes. `metadata_db_hdd`, `metadata_db_plus`, `metadata_db_system`, custom user databases and matching `.idx` files remain read-only diagnostics for later structured parsing.
- Game Data category `GD` remains non-playable to avoid importing patches, DLC and install data as games.


### dev23 PS3 package diagnostics
- Adds explicit `/dev_hdd0/game/*/PARAM.SFO` diagnostics instead of silently discarding read/parser failures.
- Reports parsed/failed SFO counts and category counts.
- Explicitly traces `NPUI94240`, `NPUI94451` and `SLES54819`, including whether the folder exists and the parsed TITLE/TITLE_ID/CATEGORY/CONTENT_ID/version.
- The console scan status now includes the PS3 SFO parsed/error totals.
