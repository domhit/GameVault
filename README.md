# GameVault v0.9.1

- One package version field in the database.
- Automatic migration: Game takes former `pkg_version`; Patch retains `version`; DLC version is cleared; obsolete column is dropped.
- Categories normalize to Game, Patch and DLC.
- XLSX package import retained as a documented specialized PS4 inventory import.
- Downloadable XLSX template and machine-readable schema included.
- Game Collector XML remains the standardized library import.
