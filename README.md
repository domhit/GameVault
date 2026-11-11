# GameVault v1.2.0-dev33

## PS3 MMS history semantics
- `Common.stat.timeLastUsed` is shown as **Zuletzt gespielt** only when `Common.stat.playCount > 0`.
- With `playCount = 0`, GameVault shows **Noch kein bestätigter Start** and keeps the timestamp separately as `mms_timestamp_at`.
- This prevents XMB import/registration timestamps from being mislabeled as gameplay.

## Compact PS3 scan diagnostics
- Normal scan output no longer includes page profiles or cross-page string dumps.
- MMS summary reports decoded records, confirmed starts, records without confirmed starts, inventory matches, and inventory misses.
- Full decoded source records remain available in `history_records` for diagnostics.

## Safe scope
- Only the validated `/dev_hdd0/game` GameHistory layout is persisted.
- GameData/additional-content records remain excluded from confirmed gameplay when `playCount = 0`.
- Disc/ISO history such as BCES00081 and SaveData parsing remain separate structural parser work; dev33 does not guess their offsets.
