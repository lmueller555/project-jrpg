# Bridge crew source and review status

The mason uses the approved `male_01` moss/tan appearance; the surveyor uses
approved `male_03` slate/brown. Their existing directional idles, walks, palettes
and layered source parts are read-only. These are new regional identities, not
instances of the grain farm's workers or town villagers.

`tools/build_bridge_workers.py` assembles the new work, measure, offer, receive,
sitting and drinking poses from the approved front-walk layers, with explicitly
registered arms and seated legs. It uses the existing generated
`../grain_workers/pose_reference.png` as a grip/weight reference; no new generated
plate is claimed. `tools/build_bridge_props.py` now registers the existing regional bench,
fence and bridge rubble into the original prop canvases. It reuses the
sanctuary kettle/cup and workshop timber surface for the tea station. Hard-pixel
nearest-neighbour crops retain material texture, directional shading, grain and
chipped masonry. Small tray edge finishes, tool bevels and check/cross markings
use the source material palettes. Exact source SHA-256 hashes, crop boxes and
unchanged output dimensions are recorded in `props_export.json`.

Cup and stone carry poses retain four approved walking leg phases; a blocked
carrier freezes the feet. All frames use a 40×44 canvas and [20,38] anchor.

The new poses and props are **review**, not newly approved art. The props are derivatives of existing game art; seated legs and action arms
remain programmatic assemblies. No new image-generated plate is claimed. The actual-game review captures document
their current appearance at normal regional zoom. Approved inputs are unchanged.
