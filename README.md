# GameVault v1.2.0-dev18

## Incremental Xbox size scan
- **Größen aktualisieren** now scans only games whose `installed_size_bytes` is still empty by default.
- Existing cached sizes are skipped, so adding one new Aurora game normally traverses only that new game path.
- A maintenance choice allows **Alle Größen neu berechnen** when a full refresh is explicitly wanted.
- The result shows newly checked, cached, remote-skipped and failed counts plus the total cached console size.

## PS3 size scan
The same separate/manual size scan is now available for PS3 consoles.

- Local `/dev_hdd0/PS3ISO/*.iso` is measured directly via FTP `SIZE`.
- Local folder/JB games are recursively summed over FTP.
- Existing cached sizes are skipped by default.
- webMAN `/net0`, `/net1`, etc. are deliberately reported as remote/not measurable through the PS3 FTP provider and are not stored as `0 B`.
- Sizes use the existing `BIGINT` byte storage and human-readable MB/GB/TB display.
