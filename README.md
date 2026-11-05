# GameVault v0.6.4

## All covers local
GameVault now treats a cover as valid only when it is cached locally under `/covers/...`, backed by `/volume1/docker/gamevault/data/covers`.

- The UI no longer requests old Game Collector paths or external cover URLs directly.
- New **Cover lokal speichern** action migrates the collection:
  1. keep existing local covers;
  2. download an existing valid remote cover URL locally;
  3. clear unusable legacy Game Collector paths;
  4. try the PS4/PS3/PS2 provider cascade;
  5. fall back to IGDB, first by known IGDB ID and then by title + platform.
- `Cover fehlt` and metadata quality now count only genuinely local covers.
- New endpoint: `POST /api/covers/localize`.
- IGDB/manual apply also replaces non-local legacy covers with a local IGDB image.

Persistent location: `/volume1/docker/gamevault/data/covers`.
No re-import and no database reset is required.
