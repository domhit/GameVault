# GameVault v1.1.0-dev4

Fourth PS3 Console Inventory development build.

## Console-driven library import
Unknown PS3 inventory entries now offer:

- **Vorhandenem Spiel zuordnen** when fuzzy PS3-library suggestions exist.
- **Als neues Spiel übernehmen** even when no suggestion exists.

Creating from the console scan:

1. validates the PS3 Serial;
2. prevents duplicates when the Serial already exists;
3. creates a PlayStation 3 library game with `SERIAL` and `console_scan` provenance;
4. links the installed inventory row immediately;
5. detects ISO format from the source path/type;
6. searches IGDB for PlayStation 3;
7. applies an unambiguous match, including local cover download;
8. otherwise stores the best result for manual IGDB review.

This establishes the reusable pattern for future Nintendo and other console providers where no prior collection list exists.
