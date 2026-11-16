# GameVault v1.2.0-dev38

## Cross-platform console play history
- Xbox 360/Aurora: reads `UserRecentGames`, maps `ContentId -> ContentItems.Id -> TitleId`, decodes FILETIME, keeps newest mapped event per TitleID/profile context, never guesses unmapped historical ContentIds.
- Xbox Classic/XBMC4Gamers: `iTimesPlayed` becomes play count; `last_played` is confirmed Last Played when count > 0; `lastAccessed` is separately retained after FILETIME conversion.
- PS4/GoldHEN: valid installed app rows retain `lastAccessTime` as `last_accessed_at`; UI labels it **Zuletzt verwendet** pending exact semantic validation.
- PS3 MMS semantics remain unchanged.
- Generic installed history adds `last_accessed_at`, `history_source`, `history_profile_id`, and `history_raw_json`.
