# GameVault v1.2.0 RC acceptance checklist

Record each item as PASS/FAIL. Do not merge to `main` until every release-blocking item passes or is explicitly accepted as a known limitation.

## 1. Deployment and migration

- [ ] Pull/build `v1.2.0-rc1` using the same PostgreSQL volume as the current dev deployment.
- [ ] Application starts without SQLAlchemy/PostgreSQL migration errors.
- [ ] Existing games, packages, covers, manual metadata and console configurations are still present.
- [ ] Admin login works; Enter submits the password.
- [ ] Visitor mode still blocks administrative writes.
- [ ] Browser console shows no recurring JavaScript errors during normal navigation.

## 2. Desktop and mobile UX

- [ ] Desktop game wall uses the full width and normal page scrolling.
- [ ] Sticky search/filter bar remains usable while scrolling.
- [ ] Phone portrait shows two complete columns without horizontal clipping.
- [ ] Mobile detail view opens true full-screen.
- [ ] Closing detail restores the former library scroll position.
- [ ] Previous / selection / Next navigation works in full-screen detail.
- [ ] IGDB search, metadata editor and resolver dialogs appear above the detail overlay.
- [ ] Enter works for admin password, IGDB direct ID and other single-action inputs.
- [ ] Dates display as `dd.mm.yyyy hh:mm:ss`, not raw ISO strings.

## 3. PS3 / CFW + webMAN

### Inventory
- [ ] Full PS3 scan finishes with `errors: []` for expected FTP/webMAN sources.
- [ ] Local `/dev_hdd0/PS3ISO` entries remain category `PS3 ISO`.
- [ ] webMAN-only `/net0`/`net1` ps3netsrv titles remain category `webMAN Game` and playable.
- [ ] Installed `HG`, `1P`, `2P` content retains the native category instead of becoming `webMAN Game`.
- [ ] `GD` entries do not count as playable parents.
- [ ] Homebrew/system titles remain excluded from game candidates.
- [ ] Unknown games remain 0 unless a genuinely new title was added.

### MMS diagnostics
- [ ] `records_decoded == unique_record_title_ids` for the current expected sample unless a new physical duplicate is understood.
- [ ] `inventory_unmatched_records == 0` for the current validated library or if not 0 explainable deviation
- [ ] `aggregate_lookup_keys == unique_record_title_ids + alias_keys`.
- [ ] `game_data_titles` and `updated_titles` are plausible after a fresh scan.

### Golden titles
- [ ] Worms Revolution `NPUB30817`: play count remains correct and Last Played is plausible.
- [ ] HAZE `BLUS30094`: Game Data shown, base `01.00`, installed update `01.36`, firmware `02.2000`, Last Played plausible.
- [ ] The Evil Within `BLES01916`: Game Data shown, base `01.00`, installed update `01.05`, firmware `04.6000`, Last Played plausible.
- [ ] HAZE/Evil Within do not gain a synthetic play count.

### Sizes
- [ ] Cached local PS3 sizes survive a normal rescan.
- [ ] Missing local ISO/folder sizes can be calculated.
- [ ] `/netX` titles are reported as remote/skipped by PS3 FTP size scan, not as zero-byte local games.

## 4. PS4 / GoldHEN

- [ ] Scan reads `app.db` and `addcont.db` without error.
- [ ] Game/DLC counts match the known installation closely (current reference: 187 games + 20 DLC unless content changed).
- [ ] `playable` and `game_candidates` equal the number of PS4 Game parents.
- [ ] No valid game is lost because `contentSize` is zero.
- [ ] Recently launched reference game shows correct local Last Played time after UTC/browser conversion.
- [ ] DLC appears under the appropriate parent where matched.
- [ ] PS4 update-status workflow still works for a known CUSA.

## 5. Xbox 360 / Aurora

- [ ] Scan reads Aurora `content.db` and `settings.db` without error.
- [ ] Xbox 360 Game, XBLA and Xbox Classic parent counts look unchanged.
- [ ] Title Updates remain child content and orphan TUs are not counted as unknown games.
- [ ] RecentGames diagnostics report mapped and unmapped historical ContentIds without errors.
- [ ] A recently launched test game shows the correct wall-clock Last Played time with no extra timezone shift.
- [ ] Multi-disc games remain collapsed to one parent while retaining combined paths.
- [ ] Missing-size scan still resolves Aurora paths case-insensitively.

## 6. Xbox Classic / XBMC4Gamers

- [ ] Scan reads configured `MyPrograms6.db` without error.
- [ ] `games - merged_duplicate_rows == unique_title_ids`.
- [ ] Installed count remains stable (reference from validation: 1047 unique TitleIDs unless collection changed).
- [ ] Recently launched test game shows correct `last_played` time.
- [ ] `iTimesPlayed` remains the correct play counter.
- [ ] Database-provided installed sizes remain present after rescan.

## 7. Metadata / library / packages

- [ ] IGDB candidate search works.
- [ ] Direct IGDB-ID load works with Enter.
- [ ] User Rating and Critic Rating appear for a known IGDB title.
- [ ] Manual metadata stays protected after IGDB refresh.
- [ ] Existing local covers continue loading.
- [ ] Game Collector XML import still updates/creates expected rows in a test copy if used.
- [ ] PS4 XLSX Package import/template still works if used.
- [ ] Duplicate analysis opens and previously excluded pairs stay excluded.
- [ ] Delete preview accurately states what GameVault will remove and does not imply console/NAS file deletion.

## 8. Release decision

- [ ] No release-blocking regression remains.
- [ ] README / v1.2.0 release notes / third-party sources / backlog are current.
- [ ] Database backup taken immediately before stable deployment.
- [ ] `develop-v1.1` is fully pushed and clean.
- [ ] RC commit is identified for the stable merge.
