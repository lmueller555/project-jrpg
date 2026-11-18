# Native Iselin right-walk source

Status: right walk approved by the user. The right walk is staged separately from the live
campaign bank. Existing approved native idles, front and left walks are intact.

`keys.png` contains four complete right-facing contact/passing studies created
with `image_gen.imagegen`. `authored.png` contains sixteen complete new drawings
in chronological row-major order. The approved native right idle controls the
character design; the approved left walk supplies gait/phase guidance. This is
right-specific artwork, not a reflected finished left costume: anatomical right
is near the camera, with the mantle/brooch visible; anatomical left and its
forward braid are far-side and mostly hidden, matching the right idle.

At contact1, the near right leg reaches screen-right while the near right arm
swings back screen-left; the far arm/leg counter them. At contact9, the near
sleeve crosses the torso's front and the near leg trails, while the far chains
exchange roles. Inspect shoulder/elbow/hand and hip/knee/ankle continuity rather
than assigning one anatomical identity permanently to a screen hand slot.
Partial occlusion around passing is intentional; no extra limb is drawn to
prove a hidden limb is moving.

`tools/export_iselin_native_right_walk.py` uses hard alpha220 and whole-figure
connected extraction. The 1086×1448 master has a 4×4 grid; its rounded column
widths are 271/272 pixels. Transparent edge padding registers each source cell
at 272×362 before the common 27×36 nearest-neighbor sample. Every pose uses
the same nominal0.1 density and `[-2,-1]` destination origin. The source crown
stays at26 and the neck/waist share the same grid. Individual foot extents or
silhouette heights never determine scale or alignment.

As in the approved side-walk workflow, the approved right idle's stationary
head/face rows0–11 are restored at destination y1 after complete-figure export.
This preserves her profile and adds the same constant one-pixel walking settle
as the left direction. There is no additional per-frame/runtime bob. Mantle,
torso, arms, coat, far braid detail and legs below y13 remain authored pixels.
No moving limb is assembled, translated, stretched or rotated. Original imagegen
masters remain unchanged.

Exports are 24×36 RGBA with one artwork pixel per world pixel, draw anchor
`[12,30]`, foot anchor `[12,34]` and an unchanged 8×4 collision probe. Sixteen
35ms frames retain the560ms two-step cycle. A review-only sheet manifest uses
the existing native actor loader with approved idles and no HD override.
`registration.json` records source/reference/output hashes and per-frame facts.

See `docs/reviews/iselin_native_right_walk/README.md` for actual movement and
renderer evidence. General authoring guidance stays centralized in
`docs/SPRITE_ANIMATION_STANDARD.md`.
