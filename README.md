# GameVault v0.6.3

## v0.6 completion
- Manual **IGDB übernehmen** now overrides `metadata_locked`. The lock still protects records from unattended bulk updates.
- Manual TitleID/Serial is never removed by IGDB.
- IGDB responses now include game modes, perspectives, themes, franchises, engines and multiplayer-mode information.
- Detail view shows the extended metadata.
- Filters added: Cover fehlt, TitleID/Serial fehlt, Local Multiplayer, Local Co-op, Online Multiplayer.
- PS4 duplicate candidate API and package-preserving merge endpoint added.
- Global bottom-right activity indicator for IGDB search, IGDB apply and ID resolver actions.
- Manual IGDB apply reports which fields actually changed.

Existing PostgreSQL data is migrated automatically. No re-import is required.
