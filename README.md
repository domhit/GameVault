# GameVault v1.2.0-dev11

## Aurora FtpDll listing fix
Aurora's FtpDll can return Unix-style LIST records from `NLST`, for example:

`drwxrwxrwx 1 root root 0 Jan 01 2000 Hdd1`

GameVault now normalizes these records to the real entry name (`Hdd1`) before case-insensitive path resolution. The same normalization is applied at every directory level and in the NLST fallback used by recursive size calculation.

Expected path flow:

`\games360\50 cent bots` -> `/Hdd1/Games360/50 cent bots`

The existing dev10 diagnostics remain, so any later failure shows the database path, Hdd1 candidate, resolved path and per-component mapping.
