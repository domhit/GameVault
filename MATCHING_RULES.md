# GameVault Matching and Classification Rules

This document summarizes deliberate special rules that complement exact identifiers and provider metadata. Rules are intentionally conservative and should be extended only with real tested examples.

## Resolver order

1. Preserve an existing confirmed provider ID and refresh by that ID.
2. PlayStation: resolve the console Title ID through SerialStation, then search IGDB using the canonical name.
3. Other platforms: use the console/exporter/ROM title and its generated search variants.
4. Keep uncertain candidates in `review`; never lower the global acceptance threshold blindly.

## IGDB title variants

GameVault stores the original title unchanged. Variants are used only for search and scoring.

- Trailing English articles: `Addams Family, The` -> `The Addams Family`.
- Trailing German articles: `Wilden Fussball-Kerle, Die` -> `Die Wilden Fussball-Kerle`.
- `_s` -> apostrophe-s, e.g. `Pugsley_s` -> `Pugsley's`.
- ` _ ` -> ` & `, ` and `, or a space.
- Subtitle separators are tried as hyphen, colon, and plain whitespace.
- `Pokemon` <-> `Pokémon`; `Fussball` <-> `Fußball`.
- Reviewed localized aliases are allowed only as a small explicit table. Current example: `Pokemon - Feuerrote Edition` -> `Pokémon FireRed Version`.

## Conservative retro auto-accept

Normal IGDB auto-accept remains at **90%**. A retro candidate between **75% and 89.9%** is accepted only when all conditions hold:

- the search is platform-constrained to GB/GBC/GBA/NES/SNES;
- source title contains at least two informative tokens;
- source and candidate share at least two informative tokens;
- every informative token of the shorter title occurs in the longer title;
- numeric tokens do not conflict;
- the source is not marked as an explicit compilation/multiple-title string such as `Double Game`; an underscore alone may represent an ampersand and is not sufficient to reject a match.

This accepts examples such as `Atlantis - The Lost Empire` -> `Disney's Atlantis: The Lost Empire`, while keeping `Zombies` -> `Zombies Ate My Neighbors` in review.

## RetroArch filename parsing

- Folder is authoritative for platform: `gb`, `gbc`, `gba`, `nes`, `snes`.
- Filename text before the first parenthesis is the normalized game title.
- First parenthesis is a region only if every comma-separated value is on the known region allowlist.
- Language groups, revisions, prototypes, unlicensed markers, SGB Enhanced and GB Compatible are stored as ROM-variant metadata.
- Unexpected extensions are skipped and reported.
- One Game record is created per platform + normalized title; every ROM file remains a separate InstalledGame variant.

## Metadata quality

Retro games require title, platform, local cover and confirmed IGDB link. Release date, genre, publisher/developer and description are useful core metadata. Engine, perspectives, themes, franchise and multiplayer fields are bonus data and do not make a correctly matched retro game critical.

## Platform and original platform

The normal platform filter matches only the owned/imported GameVault platform. Derived original platforms are metadata and are exposed through the separate Original Platform filter. Platforms within 365 days of the earliest IGDB release belong to the original launch window.

## Physical and hosted content

Physical ownership is independent from digital installation, backup or ROM availability. Vita PSPemu entries remain PlayStation 1 games hosted on PlayStation Vita; RetroArch entries remain their original Nintendo platform hosted on PlayStation Vita / RetroArch.


## PlayStation Vita provider classification

The Vita provider uses hardware-validated ID families and paths.

### Native Vita content

- `PCS*` IDs are native Vita candidates and are probed at `/ux0:/app/<TITLE_ID>/sce_sys/param.sfo`.
- `CATEGORY=gd` is a base game.
- `CATEGORY=gp` under `/ux0:/patch/<TITLE_ID>` is a title update; its `APP_VER` is the installed game version when present.
- `CATEGORY=ac` under `/ux0:/addcont/<TITLE_ID>/<CONTENT>/sce_sys/param.sfo` is DLC and remains attached to its parent Title ID.
- `NPXS*` entries are system applications under `vs0` and are excluded from the game library.

### Confirmed Vita tools / homebrew excluded from the game library

`ARKSPSPHB`, `AUTOPLUG2`, `DOOM00000`, `PKGJ00000`, `PSPEMUCFW`, `SKGTLSE12`, `TFCARDPL0`, `UPDATBLOC`, `VHBB00001`, `VITADBDLD`, `VITASHELL`.

These are explicit tested IDs, not a rule that every non-PCS application is disposable.

### Playable special content preserved

- `SOSR00001`, `SOSR00002`, `THEXTECH0`: fan ports, retained as a distinct class for future dedicated handling.
- `NPOA00025`: PlayStation Mobile Lemmings, retained as PlayStation Mobile rather than discarded as homebrew.
- `RETROVITA`: RetroArch anchor; not imported as a native Vita game because its ROM collection is handled by the RetroArch inventory stream.

### PSPemu / PS1 Classics

- `SLES*`, `SCES*`, `SLUS*`, `SCUS*` entries are treated as PS1 Classics hosted by Vita PSPemu.
- Import only when `/ux0:/pspemu/PSP/GAME/<TITLE_ID>` is non-empty.
- Real tested folders contain `EBOOT.PBP`, `DOCUMENT.DAT`, `__sce_ebootpbp`, and sometimes `__sce_menuinfo`; no Vita `PARAM.SFO` is expected there.
- Library platform remains PlayStation 1; host/runtime metadata records PlayStation Vita / PSPemu.
- SerialStation resolves the PlayStation serial to a canonical name before IGDB lookup.

### FTPVita behavior

- `NLST` and `MLSD` are not relied upon because the tested FTPVita server returns `502` for them.
- Known native Title IDs are direct-probed with `RETR`.
- Classic `LIST` is used for directories where enumeration is required, such as DLC children, PSPemu presence and recursive installed-size calculation.


### Xbox resolver rules

- Xbox 360 uses the cached x360db `games.json` index. Primary and `alternative_id` values are indexed as uppercase 8-character Title IDs.
- Xbox Classic uses MobCat's JSON API by Title ID. A Title ID may return multiple regional/XMID rows; GameVault selects the most frequent canonical full name and preserves region information in the resolver result.
- Console titles are never overwritten by resolver output. Resolver names are logged and used only as canonical IGDB search input.
- Existing confirmed IGDB IDs still take priority over any title search.
- Missing or unavailable resolver data falls back to the original console title.
