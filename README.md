# GameVault v1.1.0-dev3

- PS3 scan TitleIDs are automatically written as missing library Serials for unique exact/manual matches.
- Manual installed-game matches survive rescans.
- webMAN mount links remain canonicalized; `/mount.ps3` is never stored.
- XLSX decimal parsing correctly handles numeric values, German/international decimal formats and no longer removes decimal points from `35.697`.
- **Größenprüfung** lists packages above 500 GB and offers individual divide-by-1000 correction after review.
- Existing values are never silently rewritten.
