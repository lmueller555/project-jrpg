# Eldenmere well square — layout overlay

Status: approved by the user.

`layout.json` records the local changes to the existing commons: a rounded 10×8-tile dirt clearing, reused stone paving, a 2×2-tile well ground footprint and a two-tile-wide southern path connection. Building positions, entrances, terrace heights, bridges and watercourses remain the approved foundation's geometry.

`allowed_routes.png` extends the approved route mask with the square and connector; solid collision is still applied by the runtime. The compiler adds the well's exact 48×48 blocker to the original workshop-era collision mask and adds five well approach destinations. All prior navigation destinations remain in the manifest.

The source recipe is `assets/source/terrain/eldenmere/well/recipe.json`. The current runtime map points here as its layout source and retains the foundation plan in `original_layout_source`. Flat paving and dirt never become movement blockers. The east approach is reserved for future drawing-water routines; the west side remains open gathering space.
