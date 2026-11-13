# Caelan overworld refresh sources

`travel_authored.png` is the retained, unpainted image-generation output for the
36 core travel poses. Follow-up image-generation edits strengthen eye/fringe
separation, particularly in the right-facing views, and correct the opposite
front/back run contacts so the leading leg and arm swing alternate. The four
columns and nine rows contain four idles (front/back/left/right), then walk front/back/left/right,
then run front/back/left/right, each gait row with four successive phases.

`actions_authored.png` contains 32 empty-handed body gestures, four columns by
eight rows: directional carry, crouched pickup, giving, seated/bed-edge poses,
right seated eating, right seated drinking, repair, and casting/overhead reach.
Props and effects remain owned by their existing scene renderers and exports.
These source atlases preserve the character's costume and natural anatomy.

`registration.json` records the exact authored cell rectangles, source bounds,
fixed per-atlas scale, destination positions, anchors and hashes. The gutters
were measured from the actual drawings rather than assuming mathematically
uniform rows. Export selects connected hard alpha, reduces with nearest-neighbor
sampling and places complete drawings. The native contour pass in
`tools/caelan_outline.py` then inks the one-pixel cardinal silhouette boundary
with warm near-black (18, 12, 14). Bright supported skin-edge highlights remain
readable. Alpha, clear gaps, enclosed shading and registration stay unchanged;
no limbs are interpolated, enlarged or warped. The shared alpha extraction
helper is the same one used for Mira's authored art.

The same contour policy reaches world-action derivatives through their body
inputs and the four independently authored Caelan rescue-assistance frames.
The retained closed-eye head and separate gearblade world drawings already
have dark authored outlines. Combat and larger cinematic art are separate banks.

`legacy/` retains the preceding Caelan runtime artwork and dependent-source
inputs for provenance, before/after comparison, and unchanged prop/FX reuse.
Historical review/approval records elsewhere in the repository are also retained.
New artwork is marked **review**, not retroactively marked user-approved.

Run `python tools/build_caelan_overworld.py` to rebuild current exports and add
`--check` to compare without writing. Review at native size and the actual game
zoom; numerical registration tests alone do not certify anatomy or quality.
