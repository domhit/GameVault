# GameVault v1.2.0

Stable release for the Sony + Xbox console-inventory milestone.

## Highlights

- Unified inventory for PS3, PS4, Xbox 360 and Xbox Classic.
- Read-only console/database acquisition paths.
- Cross-platform Last Played presentation and available play counters.
- PS3 MMS structural parser with Game Data/update enrichment for ISO/disc titles.
- PS3 webMAN-aware local + ps3netsrv inventory merging.
- PS4 GoldHEN app.db/addcont.db inventory and last-access history.
- Xbox 360 Aurora ContentItems/TitleUpdates and UserRecentGames history.
- Xbox Classic XBMC4Gamers metadata, size and play history.
- Responsive desktop/mobile UX improvements and IGDB ratings.

## PS3 validation cases

- Worms Revolution NPUB30817: executable MMS path, `playCount=2`, Last Played retained.
- HAZE BLUS30094: ISO + Game Data, patch `01.36`, Disc/ISO activity timestamp validated.
- The Evil Within BLES01916: clean pre-start baseline; Game Data after first start; patch `01.05` after update; subsequent clean start updates `Common.timeModified`.

## RC acceptance

The checklist in `RELEASE_CHECKLIST_v1.2.0.md` was passed before merging to `main` and tagging `v1.2.0`.
