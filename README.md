# GameVault v1.2.0-dev1

First Xbox 360 / Aurora Console Inventory development build.

## Aurora provider
- Add Xbox 360 consoles from **Meine Konsolen**.
- Aurora FTP defaults: port 21, `xboxftp` / `xboxftp`.
- Optional NOVA endpoint defaults to port 9999 with `xboxhttp` credentials.
- Connection test checks FTP and NOVA independently.
- Read-only FTP discovery searches common Aurora database locations.
- Downloads and introspects Aurora `content.db` locally with SQLite.
- Extracts title, eight-character hexadecimal TitleID, path/storage and version when present.
- Deduplicates discovered content by TitleID.
- Reuses GameVault's installed-game matching and console-driven create-game workflow.

## Diagnostic-first dev build
Aurora database schemas vary by installation/version. The scan response includes discovered database paths, table/column schemas, rows examined and errors. A real Aurora scan will be used to refine dev2 without guessing the exact schema.

PS3 FTP/webMAN support from v1.1 remains available.
