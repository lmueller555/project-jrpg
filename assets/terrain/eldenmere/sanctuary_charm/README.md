# Sanctuary charm — approved

- `sanctuary_review.gif`: enlarged 4× looping courtyard with Caelan for scale.
- `sanctuary_review.png`: opaque RGB still of the same scene.
- `town_review.png`: 2× town overview, retaining Caelan in the town commons.
- `lantern_variants.png`: unlit and warm-pane entrance comparison, at 8×.
- `bell_cue.gif`: enlarged event-cue demonstration, repeating after a pause.

Native assets use 24px terrain and the existing 216×216 sanctuary registration
at world position (252,84). `charm.json` supplies source pack references,
placements and timing. `scene_frames/` stores **432×408 native courtyard crops**,
not complete town frames; `review_crop` gives their origin and extent.

`layers/structure.png` excludes the hanging lantern body. Add the matching
216×216 `layers/lantern/` or `layers/lantern_lit/` phase, then `layers/smoke/`.
For the garden, add the exported `props/` at the recipe's world positions;
the herb/vine wind poses replace their rest images. Imported foliage wind poses
use the recorded phase offsets. Reused roots, trunks and shadows are fixed.

The bell is already present and still in the ambient structure. To play a cue,
use `layers/bell_fixed_structure.png` and a `layers/bell_cue/` pose as the base
building, then compose the other layers. The bell cue plays once in game;
only its review GIF repeats. Its first/last pose restores the approved bell.
Lantern sways by at most one pixel; bell swing reaches two pixels at its base.
The paired doors remain closed with their original pixels.

`navigation/` adds prop footprints to the approved town planning mask and checks
a 24×12 actor probe between the doorway, stairs, bench and conversation space.
These are art/layout checks. Collision, interactions, morning/festival events,
time of day and sanctuary interior transitions are not implemented.

Build with `tools/build_eldenmere_sanctuary_charm.py`; verify with
`tools/test_eldenmere_sanctuary_charm.py`. This pack leaves all existing art,
town geography, story and quests unchanged. The exterior, garden dressing and
animations are approved for main; original review images remain as the visual
approval record.
