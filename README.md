# GameVault v0.7.1

## Metadata editor viewport fix
- The metadata editor is now a three-part layout: fixed header, independently scrollable form body, fixed footer.
- Save/Cancel remain visible at 1920x1080 and other short desktop viewports.
- Uses `100dvh` with `100vh` fallback for iPad/iPhone browser chrome behavior.
- The form uses momentum touch scrolling on iOS (`-webkit-overflow-scrolling: touch`) and `touch-action: pan-y`.
- On phones the editor becomes a full-screen, one-column sheet with safe-area-aware footer buttons.
- On desktop/tablet the editor stays two-column where space permits.
- Background scrolling is locked while the editor is open.

All v0.7.0 metadata-quality, mobile-dialog, PriceCharting, local-cover, IGDB and backlog functionality is preserved.
