# Full-body Rhea awakening study

These eight frames are an isolated review asset. They do not replace the
production actor, Gallery entry, or rejected portrait animation.

The source is the existing 128×128 `frozen_front_01.png` scene sprite. Its body,
clothing, staff, silhouette, alpha, and all pixels outside the small facial-feature
mask remain exact. Expression changes are authored with image_gen in the retained
reference sheet; the build script only extracts, registers, and palette-matches
those facial pixels. No expressions are procedurally painted or deformed.

`manifest.json` records source and result hashes, the exact mask, iris positions,
and expression starts relative to the isolated section. The runtime should draw
one normal world-space Rhea, zoom its camera toward her, and replace that actor's
frame with these registered frames while she remains inside the original prison.
The source frame and the expression frame must not be drawn together.

Rebuild from the repository root:

```sh
python3 tools/build_rhea_scene_awakening_study.py
```

The existing directional `release_*` scene frames can supply her turn and
breakout after the 2.2-second awakening hold. Those source frames are unchanged.
