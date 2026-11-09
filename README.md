# GameVault v1.2.0-dev7

## Effective Xbox version
- The visible Xbox installation version is now the highest locally available Title Update.
- If no Title Update exists, GameVault falls back to Aurora `BaseVersion`.
- The normal installation card labels this as **Installierter/verfügbarer Stand**.
- Parent game source/path remain separate from Title Update source/path.

## Correct parent / child model
- Scan consolidation uses `TitleID + content category` instead of TitleID alone.
- Xbox 360 Game, XBLA and Xbox Classic remain parent entries.
- Title Updates and DLC are always separate child entries.
- Multiple TUs coexist by TitleID, MediaID/version/path and no longer overwrite the parent version.
- The detail page renders **Updates und Zusatzinhalte** with separate Title Updates and DLC sections.

## Console provider strategy
GameVault now documents and follows this preferred source order:
1. console-maintained database or API;
2. structured manifests such as PARAM.SFO;
3. filesystem/FTP scan;
4. optional enrichment source.

Aurora uses FTP as transport for `content.db` / `settings.db`. PS3 currently uses PARAM.SFO plus webMAN because no equivalent authoritative database has yet been integrated. Future GoldHEN and Nintendo providers should prefer their structured databases/manifests when available.
