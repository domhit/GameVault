# GameVault v1.2.0-dev10

Aurora paths are treated as Hdd1-relative. `\Games360\...`, `\Content\...` and `\XboxClassic\...` are prefixed with `/Hdd1` before FTP traversal.

Every path component is resolved case-insensitively against the actual FTP listing, so database `\games360\50 cent bots` resolves to `/Hdd1/Games360/50 cent bots`.

The size-scan result reports FTP root entries, database path, Hdd1 candidate, resolved path, per-component case mapping and FTP errors. Failed paths are not cached as 0 B.
