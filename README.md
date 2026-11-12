# GameVault v1.2.0-dev34

## Unified responsive library wall
- Desktop split view is replaced by a responsive game wall using the full available width.
- Game cards keep a large cover plus title and platform metadata; they are not reduced to bare covers.
- The grid uses automatic columns on desktop/tablet and two compact columns on phones.
- Search, platform selection, metadata filters, counts, console/platform tiles, selection state, updates, resolver/admin features and all backend functionality remain intact.

## Game-mode icons on cards
Cards show compact icons only when metadata positively confirms a capability:
- 👤 Singleplayer
- 👥 local multiplayer
- ▣ split-screen
- 🤝 local/couch co-op
- 🌐 online multiplayer
Unknown capabilities display no icon rather than guessing.

## One shared detail view for desktop and mobile
- Clicking a card opens the existing full detail content in a large responsive overlay.
- No detail information was removed: metadata, value, quality, description, multiplayer, installations, versions, sizes, PS3 history, TU/DLC, packages and admin actions remain.
- Sticky header: **Zurück**, current game title, platform.
- Sticky footer: **Vorheriges**, **Für meine Konsole vormerken / ✓ Vorgemerkt**, **Nächstes**.
- Previous/next follow the current filtered/search result list, not the full library.
- Closing the detail restores the previous library scroll position without rerendering the user back to the top.
- Browser/Android Back closes the detail overlay first.
