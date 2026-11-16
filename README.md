# GameVault v1.2.0-dev43-fix3

Final PS3 parent classification refinement:
- webMAN is authoritative for whether PS3 disc/folder/net content is playable, but does not overwrite a more specific content type.
- Installed FTP/PARAM.SFO content (HG/1P/2P/etc.) remains its specific installed parent even when also listed by webMAN.
- Local FTP `PS3 ISO` / folder entries remain their specific content type; webMAN confirms availability.
- webMAN `/netX/...` entries become canonical parents when no local/installed content with that TitleID exists, preserving ps3netsrv support.
- FTP HDD `GD` remains enrichment-only and can never promote itself to playable.
- MMS Game Data, patch/version/firmware/history enrichment remains attached by TitleID.
- Disc/ISO Last Played continues to use only `Common.timeModified`.
