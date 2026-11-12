# GameVault v1.2.0-dev35

## Desktop game-wall fixes
- Restores normal browser/document scrolling for the full cover wall.
- Removes the old 1500 px shell cap; the library now uses the full available viewport width with only a small responsive outer margin.
- Desktop card grid uses `auto-fill` across the entire viewport, so wide/ultrawide screens gain additional columns instead of stopping around seven.
- Search/filter bar remains sticky while the document scrolls.
- Library scroll position is stored/restored through the actual document scrolling element.

## Mobile portrait detail fullscreen fix
- The shared game detail overlay explicitly owns `100vw × 100dvh` on phones, independent of inherited dialog/detail sizing.
- Overlay and shell are pinned to `inset: 0`, with all max-width/max-height restrictions removed in the mobile breakpoint.
- Portrait hero/information layouts are forced to use the full content width.
- Landscape behavior remains fullscreen and responsive.
- Sticky detail header/footer and Previous / Mark for console / Next navigation are unchanged.
