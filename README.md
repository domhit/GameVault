# GameVault v1.2.0-dev13

## Xbox size storage fix
The dev12 FTP traversal is retained unchanged. It successfully reaches real Aurora game files; the remaining failure was PostgreSQL storage.

- `installed_games.installed_size_bytes` now uses PostgreSQL `BIGINT` / SQLAlchemy `BigInteger`.
- Startup performs an idempotent `ALTER COLUMN ... TYPE BIGINT`, so databases where dev8-dev12 originally created the column as 32-bit `INTEGER` are repaired automatically.
- Raw sizes remain stored exactly as bytes for safe arithmetic and totals.
- The UI never presents raw bytes for normal game sizes. It formats values automatically as KB, MB, GB or TB, using German decimal commas, e.g. `7,42 GB` or `1,73 TB`.
- Existing dev12 CWD-based Aurora FtpDll traversal remains unchanged.
