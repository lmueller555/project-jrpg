# Mira workshop exterior — review

- `workshop_review.gif`: 4× enlarged, 10.8-second looping exterior and upper bridge scene.
- `workshop_review.png`: opaque RGB still of the same review.
- `exterior_review.png`: 6× isolated exterior and yard, with Caelan for scale.
- `town_review.png`: 2× updated town overview, retaining the approved sanctuary garden.
- `town_native.png`: complete native town still; Caelan remains in the commons here.

`workshop.json` describes the 168×168 drawing frame, 120×72 ground footprint,
source components, separate props, timings and positions. The native origin is
(564,264), with ground beginning at (576,360). `structure.png` includes the fixed
wall-mounted tool rack and sign bracket. Add one `sign/` pose and one `smoke/`
pose to animate it. `closed.png` is the rest sign with no smoke; `frames/` stores
54 composed building poses. Ground props are composed separately at their
recorded world positions. No autonomous mechanism is shown moving.

`scene_frames/` contains 432×312 native **cropped** scene frames, at the
`review_crop` origin, with unchanged Caelan and Mira for scale. The sign and
grass use 5.4s cycles; smoke uses the approved 3.6s cycle. GIF palette indices are
encoded before integer enlargement, preserving every native RGB pixel.

The new dirt apron reuses approved blob tiles and connects to the existing
approach. `navigation/` adds the prop footprints to the approved sanctuary/town
planning mask. The full-width 24×12 actor probe reaches all previous town
destinations, the workbench, new doorway and clear 48×48 conversation area.
The upper lane, bridge and woodland access remain open.

The workshop replaces its measured placeholder in this new composed view.
Existing input files and the original foundation exports remain unchanged.
The source recipe lives under `assets/source/terrain/eldenmere/workshop/`;
build with `tools/build_eldenmere_workshop.py`, verify with
`tools/test_eldenmere_workshop.py`.

Status: review. This is exterior art and layout, with no workshop interior,
engine collision, door interaction, map transfer or MQ02 solution implementation.
