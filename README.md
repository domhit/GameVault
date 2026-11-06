# GameVault v0.7.2

## Data quality & duplicate cleanup
- New **Datenqualität** view lists critical/optional metadata gaps, missing identifiers, missing local covers and review cases.
- New **Duplikate** view finds high-confidence same-platform duplicates.
- PS4 duplicate matching uses matching TitleID first, IGDB ID and normalized title as additional signals.
- Merge preview shows preferred keep/merge records and conflicting fields.
- Merge keeps the preferred record (Game Collector is preferred), moves all packages, inherits only missing fields and removes the duplicate.
- Existing collection value/completion data is protected by target-wins conflict handling.
- The v0.7.1 responsive editor and mobile behavior are preserved.

## Backlog
Priority B adds PS4 **Update verfügbar**: compare latest known CUSA update against archived patch packages, with `Aktuell`, `Update verfügbar`, and `Unbekannt`. No PKG downloading.
