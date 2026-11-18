# Shared Sanctuary caretaker native identity

This is the original silver-haired clean-shaven man in cream shirt and teal
sash, shared by arrival and rescue. The female reserve gardener is untouched.
Four48×72 directional idles,32 walk frames at70ms each (560ms cycle), unchanged
72×72 portrait, and the separately staged unhook/receive dependency now bind
both roles. World anchors, speed, collision, paths, rope events and rescue timing
are unchanged. Portrait identity is preserved byte-for-byte.

Idles/action master: complete authored pixel drawings. Walk source: explicit
compatible adult_man_03 complete-pose contour guides, redrawn with this actor's
head/cream shirt/brown trousers and anatomically sided teal sash. No finished
sprite mirroring, limb rig or idle warp. Source files retain all contour data;
`export.py` and `export_walks.py` reproduce the exports. Motion guides retain a
stylized stride, not a claim of perfect world-speed foot locking. Walking cloth
has simplified native contour shading relative to the source idle texture.

Inspected four direction numbered strips and normal/half-speed previews, plus
actual arrival playback through359100ms updates. `caretaker_care.png` captures
the real rope approach/unhook at400ms, with nearby post and natural arm reach;
scene completed and opened the rope normally. Diagnostic camera centered on
caretaker at960×640 native. On-scene bank overlaid into full reference checkout;
base scene state/collision and code otherwise unchanged. No need to stretch arm
to make its pixels exactly coincide with historical hand-coordinate targets.

Focused tests cover two consumer identity equality, native frames,560/1600ms
cadences, logical anchors and complete activity dependencies. Full merged-tree
rescue end-to-end, Gallery restart, save/focus and reduced-motion suites remain
required. No blanket acceptance of those unrun flows is claimed here.
