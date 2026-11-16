# GameVault v1.3 development

Current build: **v1.3.0-dev1**  
Branch: **develop-v1.3**  
Container channel: **ghcr.io/domhit/gamevault:dev**

## Baseline

v1.3 starts from the validated v1.2.0 stable release. PS3, PS4, Xbox 360 and Xbox Classic behavior must remain regression-compatible while Nintendo providers are added.

## Nintendo targets

1. Nintendo Switch / Atmosphere
2. Wii U with CFW/homebrew access
3. Nintendo 3DS with CFW/homebrew access

For each platform, identify authoritative installed-title databases/manifests before adding directory-crawl fallbacks. Reuse the existing `ConsoleProvider` / `InstalledGame` model, separate inventory from history/enrichment sources, preserve manual mappings across rescans, and expose source-row/deduplication diagnostics.

## dev1

- Version line moved to `1.3.0-dev1`.
- GitHub Actions dev branch configured for `develop-v1.3`.
- `:dev` container tag follows `develop-v1.3`.
- Documentation moved from release-candidate wording to active v1.3 development wording.
- No Nintendo provider has been introduced yet.
