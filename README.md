# GameVault v1.2.0-dev41

## Platform-aware history timezone rendering
Fixes the double timezone conversion found by real-console validation.

- PS3 MMS timestamps are canonical UTC and use `timezone_mode=utc`; the browser converts them to local CET/CEST.
- PS4 app.db timestamps are normalized to UTC in the provider and use `timezone_mode=utc`; the browser converts them to local CET/CEST.
- Xbox 360 Aurora history is already validated against local console time in GameVault and uses `timezone_mode=local`; the frontend now only reformats its date components and performs no second timezone shift.
- Xbox Classic `last_played` is already local and also uses `timezone_mode=local`.

All history timestamps continue to display as `dd.mm.yyyy hh:mm:ss`. Other application timestamps (scan/check dates) keep their normal UTC-to-browser-local behavior.
