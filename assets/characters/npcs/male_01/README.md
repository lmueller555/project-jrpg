# Town NPC — male variant 01

All four directional idles and this palette are approved by the user in chat. This is the first of three male palette variants.

- Short, tidy brown hair and two visible eyes.
- Plain moss-green work shirt, tan trousers, a simple brown belt and brown boots.
- Relaxed front-facing idle at 24×36 pixels, with the shared `[12, 34]` foot anchor.
- Simple clothing and a compact hairstyle distinguish him from Caelan and Mira.

## Files

- `idle_front.png`: native sprite with hard transparency.
- `idle_front.json`: frame, anchor, review status and palette reference.
- `idle_front_review.png`: 24× nearest-neighbor preview on a solid light background.
- `scale_comparison.png`: Caelan, this NPC and Mira at the same enlarged scale.
- `palette.json`: named material colors for later variants.

The generated appearance source and export recipe are retained under `../../../source/characters/npcs/male_01/`. The native front sprite is approved. Walking frames are the next planned assets. Palette variants retain this base silhouette and use named material colors.

## Approved directional idles

- `idle_left.png`, `idle_right.png`, `idle_back.png`: new transparent 24×36 stationary views; direction names indicate facing on screen.
- Matching `idle_<direction>.json` files record each frame's approved status, anchor and sources; `idle_<direction>_review.png` files are 24× previews.
- `idle_directions.png`: native 96×36 strip ordered front, left, right, back.
- `idle_directions.json`: frame rectangles and individual approval statuses.
- `idle_directions_review.png`: labeled 12× view of all four directions.

The new appearance sources and export settings are under `../../../source/characters/npcs/male_01/directions/`. Compare all three palettes in `../male_idle_directions_review.png`. The front frame remains unchanged.
