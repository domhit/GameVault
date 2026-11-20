# GameVault Backlog

## Active development

- **v1.5 / PlayStation Vita** on persistent branch `develop`: real-hardware discovery first. Identify authoritative installed-title data, Title ID/Content ID, versions, DLC/update relationships, storage and installed sizes before choosing FTP-only integration or a dedicated exporter.

## Console inventory

- **PlayStation Vita CFW**: native Vita inventory provider implemented in dev2 from `app.db` + App/Patch/DLC `PARAM.SFO`; next validate real-hardware scan results, then add sizes and evaluate PSP/PS1/RetroArch as separate inventory streams.
- **Nintendo Switch / Atmosphere**: deferred until the test console is available again. Follow the same real-hardware-first provider approach.
- Determine reliable installed-size data for **Wii U** titles and **Wii/vWii** content without expensive full directory walks where possible.
- Investigate reliable Xbox 360 DLC inventory and active/disabled Title Update state.
- Optional `ps3netsrv`/NAS mapping so `/netX` PS3 games can obtain sizes from the NAS.

## Library and metadata

- Extend manual/offline platform support beyond Nintendo 64, SNES and Game Boy where useful.
- Saved filters and tag manager / bulk tagging.
- Continue improving platform-specific/original release handling for unusual ports, remasters and Virtual Console/inject edge cases when real examples appear.
- Restore/extend remote update availability where authoritative public sources exist.

## Backup and operations

- Backup/restore bundle for PostgreSQL dump, covers, JSON/CSV exports and non-secret configuration.
- Credential encryption / secret-store strategy; console credentials are currently stored in PostgreSQL.
- Background/cancellable console size scans if synchronous scans become too slow.
- Content-change detection to avoid recalculating unchanged folder sizes.

## Historical / research

- Further PS3 MMS field/type decoding and optional SaveData/trophy historical-footprint support without conflating SaveData timestamps with Last Played.
- Console timezone property and canonical UTC normalization for providers that expose local wall-clock timestamps, especially Aurora history.


### v1.5.0-dev11
- Fix VitaShell FTP mount paths to use `/ux0:`, `/uma0:`, `/imc0:` and `/ur0:` exactly as exposed by FTPVita.
- Vita scan diagnostics now report the probed path and FTP listing errors instead of silently returning zero directories.


### v1.5.0-dev11
- Replace unsupported FTPVita `NLST` directory enumeration with `CWD` + `MLSD`.
- Restore the previous FTP working directory after every Vita directory probe and report CWD/MLSD failures separately.


### v1.5.0-dev11
- Remove the Vita base-game dependency on unsupported FTP directory listing commands.
- Use the 85 Title IDs from `app.db` and directly probe each mount's `app/{TITLE_ID}/sce_sys/param.sfo` via RETR.
- Retain classic `LIST` only as a best-effort enumeration method for DLC child folders.


### v1.5.0-dev11
- Route Vita `PCS*` IDs directly to `/ux0:/app/<TITLE_ID>/sce_sys/param.sfo` based on real hardware.
- Correct known imc0 homebrew IDs (`DOOM00000`, `TFCARDPL0`) and exclude them before filesystem probing.
- Classify SLES/SCES/SCUS/SLUS IDs as PSPemu entries under `/ux0:/pspemu/PSP/GAME` without expecting PARAM.SFO.
- Classify NPXS IDs as vs0 system applications.
- Add explicit counts and failure examples for PCS IDs and direct SFO RETR probes.


### v1.5.0-dev11
- Do not count Vita Title Update and DLC child rows as unknown standalone games.
- Add confirmed Vita utility/homebrew IDs including AutoPlugin II, iTLS-Enso, PKGj and VitaDB Downloader.
- Classify SOSR00001/SOSR00002/TheXTech as fan-port entries and NPOA00025 Lemmings as PlayStation Mobile for later dedicated import handling instead of deleting them as homebrew.


### v1.5.0-dev11
- Add SerialStation API as canonical PlayStation Title-ID -> game-name resolver before IGDB search for PS1/PS2/PSP/PS Vita/PS3/PS4.
- Correct the normal platform filter to match only the owned GameVault platform; original platforms are available only through the dedicated Originalplattform filter.
- Add PSPemu PS1 inventory from non-empty `/ux0:/pspemu/PSP/GAME/<SLES|SCES|SCUS|SLUS>` folders, keeping the app.db title as fallback.


#### v1.5.0-dev11
- Finalize Vita PSPemu PS1 Classic inventory: only non-empty SLES/SCES/SCUS/SLUS directories are imported.
- Keep PS1 as the library platform while recording PlayStation Vita / PSPemu as the host/runtime source.
- Mark Vita-hosted PS1 Classics as Digital with storefront `PS1 Classic / PSPemu`; SerialStation resolves the canonical name from the PlayStation serial before IGDB lookup.
- Research authoritative Title-ID/name resolver sources comparable to SerialStation for Xbox/Xbox 360 and Nintendo platforms before changing those resolvers.


##### v1.5.0-dev11
- Add PS Vita size scans using FTPVita `LIST` recursively, which is hardware-confirmed by PSPemu/addcont enumeration.
- Measure native Vita base games, patches, DLC and Vita-hosted PS1 Classics independently and cache each InstalledGame size.
- Default to missing-size-only scans; forced full recalculation remains available.


###### v1.5.0-dev11
- Store Vita Title Update inventory paths as `/patch/<TITLE_ID>` directories instead of the nested `sce_sys/param.sfo` file.
- Size scans normalize existing legacy patch-file paths to the patch root before recursive FTP traversal.
