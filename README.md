# GameVault v1.2.0-dev8

## Separate Xbox game-size scan
- Xbox/Aurora consoles now provide **Größen aktualisieren** separately from the fast inventory scan.
- GameVault uses Aurora's known game paths, then recursively sums only those paths via read-only FTP.
- Xbox 360 Game, XBLA and Xbox Classic are scanned. Title Updates and DLC keep their own Aurora file-size metadata and are not re-counted as parent game size.
- Multi-disc paths separated by `|` are summed.
- Results are cached in PostgreSQL as bytes plus `size_checked_at`.
- A normal Aurora inventory rescan preserves cached sizes when TitleID, category and path remain unchanged.
- Console cards show cached total size and how many games have a calculated size.
- Game details and console inventory show the calculated game size.

## Safety and performance
- The size scan is read-only and never changes console files.
- It is intentionally manual because recursively walking hundreds of game directories can take much longer than downloading Aurora's databases.
- FTP `MLSD` is preferred; `NLST`/`SIZE` is used as fallback for Aurora FTP servers with limited command support.
