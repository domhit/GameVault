# GameVault v1.2.0-dev27

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


### dev24 PS3 PARAM.SFO parser fix
- Fixes the PSF header parser: PARAM.SFO has five header values (magic, version, key-table offset, data-table offset, entry count).
- dev23 unpacked five values into four variables, causing every `/dev_hdd0/game/*/PARAM.SFO` to fail with `too many values to unpack (expected 4)`.
- Retains the dev23 diagnostics so package categories and the three target titles can be verified after the fix.


#### dev25 PS3 XMB metadata_db_hdd diagnostics
- Reads `/dev_hdd0/mms/db/metadata_db_hdd` read-only during the PS3 inventory scan.
- Adds a conservative diagnostic parser for Game-like records and reports unique title IDs, nearby titles, original/sub IDs, directory paths and version-like fields.
- Explicit target diagnostics remain for NPUI94240, NPUI94451 and SLES54819.
- `metadata_db_plus` and `metadata_db_system` are intentionally not parsed or imported.
- dev25 does not create inventory rows from MMS data yet. The parser first validates the structure against the real console output, avoiding system/homebrew false positives.


#### dev26 PS3 package identity and classification
- Stores the `/dev_hdd0/game/<folder>` package ID as `content_id` when it differs from PARAM.SFO `TITLE_ID`; e.g. NPUI94240 + SCUS94240.
- Cleans trademark symbols and normalizes `Syphon Filter®2` to `Syphon Filter 2`.
- Separates `playable`, `game_candidates`, `non_game` (`GD`, `SF`) and known `homebrew` counts.
- Keeps HG visible but excludes known homebrew titles from game candidates.
- Reports the exact folder/path/error for failed PARAM.SFO files.
- Removes `.` and `..` from MMS diagnostics.
- Keeps metadata_db_hdd diagnostic-only; plus/system remain ignored.


#### dev27 PS3 scan cleanup and structural MMS parser foundation
- Filters `.` and `..` globally from FTP directory listings, so false PARAM.SFO failures disappear.
- Adds detailed `unknown_items` and `homebrew_items` output with title, identifiers, category, platform, path and source.
- Replaces the unsafe nearby-string MMS record heuristic with a schema-driven foundation using `/dev_hdd0/mms/db/md_schema.scm`.
- Verifies the required Common/Game fields from the real schema and reports exact title-ID occurrences and offsets.
- No longer emits guessed MMS titles, original-ID relationships, paths or versions.
- Full object-page decoding is deliberately the next parser stage; MMS remains diagnostic-only until records can be decoded by schema-defined layouts.
