# GameVault v1.2.0-dev21

## PS4 installed-game filter refined
The GoldHEN `app.db` provider now treats a row as an installed PS4 game only when all of these are true:

- `titleId` matches `CUSAxxxxx`
- `uiCategory = game`
- `category` is `gd` or `gp`
- `metaDataPath` starts with `/user/appmeta/`

`contentSize` is deliberately **not** a filter. Real playable and visible titles can report `0` in that field.

This excludes the validated Destiny residual/system entries (`gdi`, `/system_ex/app/...`) without hard-coding Destiny or relying on `visible`/size heuristics.

The scan diagnostics now break ignored rows down by invalid CUSA, non-game UI category, unsupported category, metadata path, and duplicate CUSA.
