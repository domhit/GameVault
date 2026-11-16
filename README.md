# GameVault v1.2.0-dev40

## Correct PS3 MMS time decoding
`Common.stat.timeLastUsed` is an 8-byte PS3 RTC value decoded as:
- bytes 0-1: year (big endian)
- byte 2: month
- byte 3: day
- byte 4: reserved/unknown
- byte 5: UTC hour
- byte 6: minute
- byte 7: second

Validated against a real Worms Revolution launch: real 16.11.2026 12:19:15 CET, MMS raw `07ea0b10000b1310` -> 16.11.2026 11:19:16 UTC -> 12:19:16 CET.

## PS3 / PS4 timezone handling
- PS3 decoded MMS timestamps remain canonical UTC (`+00:00`).
- PS4 `app.db.lastAccessTime` is normalized from its naive database text to an explicit UTC ISO timestamp.
- Frontend uses the browser's local timezone (Europe/Berlin in the validated environment), therefore CET/CEST transitions are automatic rather than hard-coded `+1` or `+2` offsets.
- Xbox 360 FILETIME and Xbox Classic explicit history stay unchanged.

## Human-readable frontend dates
Frontend date/time rendering uses German human-readable format instead of raw ISO strings:
`dd.mm.yyyy hh:mm:ss`.
This is applied to console play history and common scan/check timestamps while raw API/database values remain ISO for reliable parsing and storage.
