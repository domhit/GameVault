# GameVault v1.2.0-dev19

## PS3 inventory deduplication
- PS3 parent inventory rows now use **platform + TitleID** as their primary identity across FTP and webMAN.
- An FTP ISO and its webMAN representation therefore become one installed game instead of two.
- FTP is preferred for canonical local path/storage and size-capable records; webMAN can still contribute a better title/version.
- Sources are combined (`FTP ISO + webMAN`).
- Existing PS3 size cache is recovered by TitleID even when the old duplicate row used a different webMAN path.

## Console card total
- Every console card prominently shows **Installierte Gesamtgröße** using cached installed-game sizes.
- Totals deduplicate parent sizes by platform + identifier, protecting the dashboard even before a legacy PS3 duplicate scan has been rebuilt.

## Console images
- Console editor accepts JPG, PNG or WebP up to 8 MB.
- Images are stored persistently under `/data/console-images` and displayed on the console card.
- Images use `object-fit: contain`, suitable for front/product shots or transparent console renders.
