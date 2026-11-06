# GameVault v1.1.0-dev1

First Console Inventory development build.

## PlayStation 3 provider
- New **Meine Konsolen** page.
- Configure PS3 name, host/IP, FTP port and optional credentials.
- Optional webMAN MOD URL.
- Read-only FTP connection test and inventory scan.
- PARAM.SFO parser for TITLE, TITLE_ID, APP_VER/VERSION, CATEGORY and CONTENT_ID.
- Scans `/dev_hdd0/game`, `/dev_hdd0/GAMES`, `/dev_hdd0/GAMEZ` and `/dev_hdd0/PS3ISO`.
- Distinguishes playable HDD games from Game Data/Patch/DLC through CATEGORY.
- Optional webMAN adapter reads `index.ps3` and `games.ps3` as an enrichment source for ISO/JB paths.
- Persists scan results in `installed_games` and matches by PS3 identifier first, exact normalized title second.
- Shows matched and unknown installed content.

## Dev1 scope and limitations
- Strictly read-only toward the PS3.
- ISO entries without webMAN may have title/path but no reliable version.
- USB/NTFS/network enumeration is primarily delegated to webMAN in this first build.
- FTP password is stored in PostgreSQL in dev1; anonymous FTP or a dedicated read-only credential is recommended.
- Real Rebug/webMAN scan results will be used to refine dev2.
