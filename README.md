# GameVault v1.2.0-dev2

Aurora inventory refinement based on a real Xbox 360 scan.

## Xbox 360
- Rejects Aurora filesystem/system pseudo rows such as Aurora, Flash, Hdd1, HddX, SysExt and System.
- Requires a valid eight-character hexadecimal TitleID for Aurora content.
- Separates Xbox 360 Game, XBLA, Xbox Classic, DLC and Title Update records.
- Games are deduplicated by TitleID and content kind; DLC/TU retain content/version distinctions.
- Scan diagnostics show examined, rejected and deduplicated rows plus content counts.
- Console cards show counts by content kind.
- Parallel scans are blocked with HTTP 409.
- Library availability badge is platform-generic, including Xbox 360.

## Console UX
- Consoles can now be edited after creation.
- Passwords remain unchanged when edit fields are left blank.
- Scan confirmation text is provider-specific for PS3/webMAN and Xbox/Aurora.
- Busy indicator remains visible for the complete scan.

PS3 inventory functionality remains available.
