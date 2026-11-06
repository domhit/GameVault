# GameVault v0.7.4

## Duplicate review improvements
- Every duplicate candidate can be expanded into a compact side-by-side comparison.
- Comparison includes cover, title, platform, TitleID/Serial, IGDB ID, release, publisher, developer, genre, franchise, value, completion status and package count.
- New **Kein Duplikat** action persists the pair in PostgreSQL and removes it from all future duplicate scans.
- Exclusions use canonical game-ID pairs, so pair order does not matter.
- Different populated IGDB IDs are now strong evidence against a duplicate and suppress false positives such as different entries from the same series.
- Different release years reduce fuzzy-title confidence.
- Merge removes stale exclusions involving the deleted record.

All v0.7.3 scrolling, metadata, quality, cover and merge behavior remains available.
