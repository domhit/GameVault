# GameVault v1.2.0-dev36

## Mobile portrait width fix
- The search/filter bar no longer forces the document wider than the phone viewport.
- On phones the search field occupies a full row, platform/metadata selectors share a second row, and the result count occupies its own compact row.
- Every grid/container/card is explicitly constrained with `min-width: 0` / `max-width: 100%`.
- Portrait keeps exactly two game columns, with both columns fully visible and long titles wrapping inside their card.
- Horizontal overflow is disabled only at the page level; normal vertical scrolling remains unchanged.

## Detail child-dialog stacking fix
- The shared detail overlay remains at z-index 250.
- Editor, IGDB, resolver/trace, confirmation and managed dialogs now render at z-index 420-440.
- Global busy indicator uses z-index 500.
- Therefore **Metadaten bearbeiten**, **IGDB suchen** and **Alle Resolver ausführen** correctly open above the game detail view instead of behind it.

## Retained dev35 layout fixes
- Full-width desktop game wall with normal document scrolling.
- Sticky search/filter bar.
- True 100vw × 100dvh mobile detail view.
- Previous / mark-for-console / next footer and scroll-position restoration remain unchanged.
