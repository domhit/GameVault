# GameVault v1.2.0-dev43
- PS3 MMS preserves multiple Game records per TitleID.
- `_GDATA_` and `_INST_`, gameCategory 6000 / bootable 0 are aggregated with ISO/folder inventory by TitleID.
- PSN/Classics keep playCount + timeLastUsed.
- Disc/ISO Last Played uses latest validated GD/INST timeModified; no synthetic play count.
- Game.version -> base version; Game.param1 -> installed patch (validated HAZE 01.36, The Evil Within 01.05); Game.ps3SystemVer retained.
- Detail history shows Game Data, base version, installed update and required PS3 firmware.
