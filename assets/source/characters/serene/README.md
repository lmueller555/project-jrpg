# Mother Serene — front idle source

**Existing asset / legacy construction reference.** New or revised artwork
follows the [global sprite and animation standard](../../../../docs/SPRITE_ANIMATION_STANDARD.md).
Part, mask, layer and registration recipes below document this pack's existing
implementation and reproduction, not the authoring method for new animations.
Approval records and original review evidence are retained.

The retained transparent concept was generated for the approved design: silver-templed brown bun, warm brown eyes, short blue-gray mantle with a plain bronze clasp, sage calf-length dress, ivory cuffs, linen apron and brown ankle boots. The apron uses button fastenings; there are no cloth ties or religious symbols. Her precise age is not established by this artwork.

Run `python tools/build_serene_idle.py` from the repository root. `export.json` retains the alpha threshold, nearest-neighbor source bands, material windows and two eye landmarks. Material windows keep similar gray, green and linen shades assigned to their intended garments. Bands preserve the shared large-head character proportions rather than shrinking the entire illustration uniformly. Eye landmarks preserve two readable pupil/iris pairs at native size. Tiny source details such as individual stitches and the hairpin may disappear at this resolution.

Four full-frame transparent layers reconstruct the native image exactly: head, bodice/arms, skirt/hands and legs/boots. These retain the original decomposition for exact reconstruction. This initial
idle export did not add walking frames or another facing direction.

The visual design and front-idle export are approved. Existing character appearances, pose templates and narrative files are read only.

## Left, right and back turnaround

`idle_turnaround_concept.png` retains the generated three-view appearance plate based on the approved front concept and native review. `turnaround_export.json` records each view's source bounds, native width, nearest-neighbor registration bands, garment material windows and eye landmarks. The profiles are independently sampled from the plate. The back has no eye landmarks and keeps the apron panel/pocket on the front; its narrow waist fastening uses buttons.

Run `python tools/build_serene_directional_idles.py`. Four full-frame layers per new direction are exported to `idle_left_layers/`, `idle_right_layers/` and `idle_back_layers/`; each stack reconstructs its idle exactly. Layers retain the original idle decomposition; this directional-idle milestone
did not add walking frames. Native frames and opaque review boards go to `assets/characters/serene/`. The approved front, its layers, concept and palette remain unchanged. All three directional idle exports are approved. Review images retain their original review labels.
