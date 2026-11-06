# GameVault v0.7.3

## Dialog UX consolidation
- IGDB result search now uses a fixed header, independently scrollable result list, and fixed footer.
- Direct IGDB ID, `ID laden`, and `Schließen` remain reachable even with many search results.
- Data Quality and Duplicate dialogs use the same fixed-header / scroll-body / fixed-footer layout.
- Mobile/iPad dialogs use `100dvh`, iOS momentum scrolling, safe-area-aware footers and touch-friendly controls.
- Duplicate merge no longer re-runs analysis after every merge. The merged candidate card is removed locally and the remaining count updates immediately.
- Duplicate dialog now provides **Neu analysieren** for an explicit fresh scan.

All v0.7.2 metadata, merge, quality, editor, local-cover and backlog functionality is preserved.
