# GameVault v1.2.0-dev9

## Aurora FTP path resolution fix
- Aurora database paths such as `\Games360\007Bloodshot` are now tested against the actual FTP namespaces discovered at `/`.
- Typical mapping becomes `\Games360\007Bloodshot` → `/Hdd1/Games360/007Bloodshot`.
- Content and Xbox Classic paths use the same device-prefix resolution.
- Existing absolute paths such as `/Hdd1/...` remain unchanged.
- Multi-disc paths are resolved and summed independently.

## Detailed size-scan diagnostics
- The scanner reports FTP root entries, candidate paths, resolved path, listing method, files, directories and status.
- An unavailable/unlistable path is an error and is no longer stored as a successful `0 B` result.
- `0 B` is stored only when a directory was successfully listed and was genuinely empty.
- Results distinguish success, partial traversal, empty directory and path-not-found/unlistable.
- The result dialog shows successful examples and up to 20 failures with all attempted paths.
