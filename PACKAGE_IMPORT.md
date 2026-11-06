# GameVault XLSX Package Import

The XLSX import is retained as a specialized PS4 package-inventory import, not as a generic library spreadsheet. Game Collector XML is the standardized library import; games can also be created directly in GameVault.

GameVault reads the first worksheet. Header names are case-sensitive.

## Required
- `Filename`: stable unique package key
- `Category`: `Game`, `Patch`/`Update`, or `DLC`/`Addon`/`Add-on`

## Recommended
- `Title ID`: PS4 CUSA used to link packages to a game
- `Name`: fallback game/package name
- `Version pkg`: source version for `Game`
- `Version`: source version for `Patch`/`Update`
- `Location`: storage volume/HDD
- `Size (GB)`: numeric size

## Optional
- `Newest Patch`
- `Entscheidung`

## Internal version rules
- Game: `version = Version pkg`
- Patch/Update: `version = Version`
- DLC/Addon: `version = NULL`

Internally there is only one `packages.version` column. Download the template from `/api/import/packages/template.xlsx` or use Import > Vorlage laden.
