# GameVault v1.2.0-dev43-fix1
- `_INST_` implies Game Data presence.
- Disc/ISO Last Played uses only `Common.timeModified`; `Game.timeModified` remains diagnostic.
- FTP HDD `GD` cannot replace a playable ISO/folder/webMAN parent.
- MMS history/version enrichment is retained on the playable parent.
- Diagnostics separate unique record TitleIDs, lookup keys and aliases.
