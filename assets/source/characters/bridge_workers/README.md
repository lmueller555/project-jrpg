# Bridge crew source and review status

The mason uses the approved `male_01` moss/tan appearance; the surveyor uses
approved `male_03` slate/brown. Their existing directional idles, walks, palettes
and layered source parts are read-only. These are new regional identities, not
instances of the grain farm's workers or town villagers.

`tools/build_bridge_workers.py` assembles the new work, measure, offer, receive,
sitting and drinking poses from the approved front-walk layers, with explicitly
registered arms and seated legs. It uses the existing generated
`../grain_workers/pose_reference.png` as a grip/weight reference; no new generated
plate is claimed. The builder creates separate cup, kettle, masonry, tool,
tray, bench and barrier props with a small hard-pixel palette. Cup and stone
carry poses retain four approved walking leg phases; a blocked carrier freezes
the feet. All frames use a 40×44 canvas and [20,38] anchor.

The new poses and props are **review**, not newly approved art. The small prop
shapes and seated leg construction are authored programmatically; they are not
claimed as image-generated exports. The actual-game review captures document
their current appearance at normal regional zoom. Approved inputs are unchanged.
