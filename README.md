# GameVault v0.6.2

- Entfernt den fehlerhaften `version_parent = null`-Filter aus der IGDB-Suche.
- Suchstrategie 1: Titel plus Plattform.
- Fallback: Titel ohne Plattformfilter.
- Direkte IGDB-ID lädt den Datensatz ohne Namenssuche.
- Diagnose: `GET /api/igdb/test/110835` muss Borderlands 2 VR liefern.
- Vollständiger Metadateneditor und Resolver-Dialog aus v0.6.1 bleiben enthalten.
