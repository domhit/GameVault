# GameVault 0.1.0

Self-hosted game collection and PS4 backup archive. GameVault imports a Game Collector v22 XML export plus the existing PS4 XLSX backup list and joins them without modifying the source files.

## First run
1. Replace `YOUR_GITHUB_USER` in `docker-compose.yml`.
2. Push the repository to GitHub. GitHub Actions builds `ghcr.io/<user>/gamevault:latest`.
3. Deploy the compose file in Portainer.
4. Open `http://<docker-host>:8080`.
5. Use **Import** to upload `games.xml`, then `PS4-Games.xlsx`.

Data persists in `./data/gamevault.db`. The initial release intentionally has no cover scraper. Game Collector image paths are saved as source metadata for a later cover import/scraper.

## Import behavior
- Game Collector XML: title, platform, publisher, developer, genres, release date, completion, collection/completeness status, values, description, IDs and original image paths.
- PS4 XLSX: filename, Title ID, versions, newest patch, decision, volume, category and size.
- PS4 packages first match a PlayStation 4 catalog game by normalized title; otherwise a technical game stub is created. Exact Title ID matching is retained for later enrichment.
- Re-import is safe: catalog records use the Game Collector ID, packages use their filename.
