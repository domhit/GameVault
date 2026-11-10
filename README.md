# GameVault v1.2.0-dev20

## PS4 / GoldHEN console provider
- New console type: PlayStation 4 / GoldHEN, FTP default port 2121.
- Reads `/system_data/priv/mms/app.db` read-only via FTP.
- Uses `tbl_appbrowse_*` plus `tbl_appinfo` for CUSA, title, ContentID, APP_VER/VERSION, installed size, install date, and internal/external HDD status.
- Reads `/system_data/priv/mms/addcont.db` as the authoritative installed-DLC source.
- DLC rows carry parent CUSA, ContentID, title, version attribute and are nested under their parent game using the existing console child-content UI.
- Main PS4 games match existing GameVault records by CUSA, so the existing package/update model can compare archived and installed versions.

## Platform/category images
- New **Plattformbilder** manager in admin mode.
- JPG, PNG and WebP up to 8 MB can be assigned per platform.
- Images persist in `/data/platform-images` and replace the PS4/PS3/360/XBOX text glyph in the category tiles.
- Existing text glyph remains as fallback when no custom image exists.
