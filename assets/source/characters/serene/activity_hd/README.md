# Mother Serene native activities

Dormant opt-in bank. `drawings.json` contains complete literal native sleeve/body
plans with the canonical native head and selected original costume-center pixels.
All body imagery comes from the named-HD identity, not enlarged legacy actor art.

44 routine frames preserve the same logical48×48 canvas, [12,6] body offset,
[24,36] draw anchor, durations, phases, prop ownership and source surface records.
PNG artwork is96×96; `artwork_pixels_per_world_pixel` is2. Source stationary props
remain in `assets/characters/serene/routines`. The top-level
`legacy_surface_prop_bank` makes that dependency explicit; do not reinterpret
those original prop rasters as native2×. Each working prop retains original art,
positions and lifecycle. Only prop layers use compatibility nearest sampling.
They sit behind the back-facing body, including legitimate full occlusion.

`story/poses.json` identifies the separate seated and bandage-aid poses, native
48×72 with logical24×36 and unchanged [12,30] draw anchor. The aid bandage retains
its original extent and palette. No other emergency actor or party pose changes.

## Existing cinematic projection retained

`assets/story/regent_arrival/actors/serene/animation.json` remains unchanged.
Its existing80×96 canvas, [40,92] anchor and separately authored detailed
cinematic projection already depict Serene's approved brown/silver bun,
blue-gray mantle and apron. It is not a24×36 game sprite requiring blind doubling.
The seven cinematic poses/walks remain their established scale and cadence.

Export from repository root after the named-HD base bank is present:

```
python assets/source/characters/serene/activity_hd/export.py --repo-root .
python assets/source/characters/serene/activity_hd/validate.py --repo-root .
```

Requires Pillow. Legacy code is imported only for its original prop-drawing
functions, never for actor reconstruction or filesystem writes. Source manifests
preserve behavioral metadata. All46 PNGs are hashed reproducibly.

Runtime activation and in-scene verification are a separate PR. This art package
does not change schedules, scripts, collision, ownership, playable party members,
the Sanctuary gardener, or any other actor's artwork.
