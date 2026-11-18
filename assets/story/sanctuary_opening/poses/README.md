# Sanctuary opening poses

Native transparent 24×36 poses reuse the approved Caelan/Tomas profiles and
front views. Each new action has four distinct key poses with variable holds.
Heads and shoulders lower together as the knees bend; boots retain the shared
baseline. Eating uses short elbow pivots, a small bite and a closed-mouth rest.
The cup gesture finishes with a glance toward Serene, without stretching arms.

Actions: `wake_up`, `caelan_sit`, `caelan_stand`, `tomas_sit`, `tomas_stand`,
`caelan_eat`, `tomas_eat`, and `caelan_seated_cup`. Their `animation.json` files
record duration, presentation kind, registration positions and wrist landmarks.
Display positions should interpolate continuously between authored keys. The
waking head begins at image `[48,123]`; its first key stays on the pillow. The
second key supplies a full body beneath the quilt, so the head never travels
alone. The body emerges at the right bed edge and finishes at the clear standing
point `[90,186]`. Head-bottom landmarks guide a dynamic blanket mask below the
chin, clipped to the bed rectangle; the face remains visible at every key.

Dining chairs stay fixed at `[120,174]` and `[192,174]`, around table `[144,168]`.
Standing points are `[108,200]` and `[228,200]`; seated display anchors are
`[138,200]` and `[198,200]`. Body draw anchors remain `[12,30]`. The original
single-pose and plate-nudge paths remain available for older scene code.

The separate 8×4 plate and 6×6 cup use approved breakfast-object colors. Cup
attachment, release frame and final table coordinates are recorded in the action
metadata. No original character or furniture PNG is changed.

Rebuild with `python tools/build_sanctuary_opening_poses.py` (Pillow required).
The builder checks hard alpha, palettes, distinct key poses and source PNG hashes.
Runtime uses only the checked-in exports; no Pillow dependency is introduced.
