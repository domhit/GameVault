# GameVault v1.2.0-dev32

## PS3 MMS play history
- The PS3 provider now downloads `metadata_db_hdd`, `metadata_db_hdd.idx`, and `md_schema.scm` together and invokes the structured three-argument parser.
- IDX-validated Game records enrich matching PS3 inventory rows by package/original TitleID.
- Persisted per-installation fields: `play_count`, `last_played_at`, and the complete decoded MMS record as JSON.
- Existing history is retained across rescans when the current MMS database does not return a matching record.
- Game details show a new **Spielhistorie** section per console with last played timestamp, launch count, and source.
- Raw structured MMS fields remain available through the API without overwriting GameVault's manual completion status.

## Safety boundary
- dev32 imports only fields decoded by the validated Game record layout (`Common.stat.playCount`, `Common.stat.timeLastUsed`, title/package/original ID, sort title, filename, directory path).
- SaveData text, completion percentages, game-specific playtime, credits, vehicles, checkpoints, and similar strings are not guessed or normalized yet. They remain diagnostic until their own schema record layouts are structurally decoded.
