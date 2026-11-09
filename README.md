# GameVault v1.2.0-dev12

## Aurora FtpDll CWD traversal
The Xbox size scanner now follows the exact behavior verified on the real Aurora FtpDll server.

FtpDll does not reliably honor `NLST /Hdd1/...`. GameVault therefore uses stateful navigation:

1. `CWD /`
2. case-insensitive `CWD Hdd1`
3. `NLST` in the current directory
4. case-insensitive `CWD Games360` / `Content` / `XboxClassic`
5. continue one directory component at a time
6. recursively sum the current directory using `CWD`, `NLST` and `SIZE`
7. restore the previous working directory after each recursion

Database `\games360\50 cent bots` therefore resolves through the real FTP names to `/Hdd1/Games360/50 Cent BotS` without issuing `NLST /Hdd1`.

Existing size-scan diagnostics remain and now report `CWD` resolution steps and the final current-directory path.
