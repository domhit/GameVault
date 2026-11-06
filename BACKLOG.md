# GameVault Backlog

## Cross-platform library model
- Group the same game across platforms into one logical game entry.
- Show every owned platform/version on the combined game page.
- Preserve platform-specific identifiers, packages, installed status and metadata beneath the shared game identity.

## Console installation inventory
Read which games are installed on the user's modded consoles. Implement per-console adapters because access methods differ by platform/CFW.

Known environment to investigate in a later release:
- Xbox 360: Aurora
- PlayStation 3: Rebug
- PlayStation 4: GoldHEN
- Nintendo Switch: Atmosphere
- Wii U: jailbreak/CFW
- PlayStation 2: FreeHDBoot
- Xbox Classic: PrometheOS + XBMC4Gamers
- Nintendo 3DS: jailbreak/CFW

Target state in GameVault: owned, backup available/location, installed console(s), installed version where obtainable, latest known update, completion and multiplayer metadata.

## Priority B - Update availability
- Restore the PS4 `Update verfügbar` feature.
- Resolve latest known PS4 update by CUSA (Sony/OrbisPatches-compatible metadata source).
- Compare latest remote version with the highest archived Patch/Update package in GameVault.
- Statuses: `Aktuell`, `Update verfügbar`, `Unbekannt`.
- Add list filter and detail badge.
- Information only: never download game/update PKG files.
