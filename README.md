# GameVault v1.1.0-dev2

Second PS3 Console Inventory development build, refined against a real Rebug/webMAN inventory.

## Improvements
- webMAN duplicates are collapsed by PS3 TitleID.
- `/mount.ps3/...` control links are normalized to their actual storage paths.
- `UNMOUNT GAME` and other control links are ignored.
- Human-readable webMAN display titles are preferred over ISO filenames.
- Storage is normalized to Internal HDD, network slots and USB devices.
- Library games now receive `installed_on` data.
- Library cards and detail pages show PS3 availability, path, storage, source and scan date.
- Filters: `Auf PS3 verfügbar` and `Nicht auf PS3 verfügbar`.
- Unknown installed titles receive fuzzy same-platform library suggestions.
- Confirmed matches can write a missing PS3 Serial into the library record.
- Manual matches are persisted until the next full scan; dev3 will preserve overrides across rescans.

## Version limitation
webMAN list pages do not consistently expose APP_VER for ISO entries. dev2 keeps the version when present and leaves it empty otherwise; it does not guess from filenames.
