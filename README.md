# GameVault v1.2.0-dev43-fix2

PS3 parent-source correction:
- webMAN is authoritative for currently playable PS3 inventory, including local `/dev_hdd0` and ps3netsrv `/netX` games.
- FTP ISO/folder results enrich webMAN with local file/size data but do not replace the webMAN parent.
- FTP HDD `GD` records are enrichment only and can never become/replace a playable parent.
- MMS `_GDATA_` / `_INST_` data enriches the canonical parent with Game Data, base version, installed patch, firmware and history.
- ISO/disc activity uses only `Common.timeModified`; `Game.timeModified` remains diagnostic.
- `_INST_` counts as Game Data presence.
- Diagnostics separate unique MMS record IDs, aggregate lookup keys and aliases.
