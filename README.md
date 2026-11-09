# GameVault v1.2.0-dev14

## Aurora whitespace bugfix
FtpDll Unix-style listings are parsed without collapsing repeated spaces in filenames. This fixes paths such as `Command  Conquer 3` and `Kane  Lynch Dead Men` while preserving the working CWD size traversal from dev13.

## Xbox Classic / XBMC4Gamers
A new ConsoleProvider reads `MyPrograms6.db` from XBMC4Gamers over FTP. The supplied real database contains a `files` table with path, title ID, title, size, developer, publisher, genre, release date, synopsis and gameplay-feature metadata.

Default database path:
`/E/XBMC4Gamers/system/UserData/profiles/Dominic/Database/MyPrograms6.db`

The first implementation deliberately imports only game rows under `\\Games\\`, excluding dashboard applications under `E:\\Apps`. `iSize` is used directly as the installed game size.

## x360db enrichment
The existing x360db provider is now surfaced as a global Xbox 360 enrichment action. x360db is matched primarily by 8-character TitleID and can fill missing title/developer/publisher/genre/release metadata and local box art before IGDB is needed. x360db documents a flat `games.json` index with these fields plus Media IDs and artwork. 

## DLC
The Xbox child-content model remains DLC-ready. This build does not invent DLC from ambiguous Aurora `ContentItems`; reliable DLC detection remains conservative until an authoritative installed-DLC structure is identified.
