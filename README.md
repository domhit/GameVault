# GameVault v1.2.0-dev39

- Fixes Aurora `recent_by_tid` initialization and implements `UserRecentGames.ContentId -> ContentItems.Id -> TitleId` mapping with FILETIME conversion.
- Xbox Classic: `iTimesPlayed` + `last_played`; `lastAccessed` retained separately.
- PS4: `lastAccessTime` is now shown as **Zuletzt gespielt**, validated by the real console.
- Generic per-installation history fields preserve source, profile and raw values.
