# Iselin rear walk — review pending

Sixteen whole-character drawings exported at42×72, using the established35ms
frame time and560ms two-step cycle. The review branch does not activate or merge
this cycle; approved front and side artwork remains unchanged.

![Normal speed on the left; half speed on the right](preview_right_foot_v2.gif)

[Numbered native drawings enlarged4×](frames_right_foot_v2.png).

The canonical reference is `assets/source/characters/iselin/idle_back_master.png`.
The mantle stays on anatomical right (viewer right); the braid turns forward
over anatomical left, so only its root/bend is visible from behind. No long
central rear ponytail is invented. The head, hair root, mantle and coat retain
the rear idle design while following the gait with small drawn variations.

Contact and passing keys were generated first. Short whole-frame transition
strips followed. The first strips exchanged legs too early in some candidates,
so a reference showing only the right-arm-trailing contact was used to redraw
the opening/closing transition. Complete poses were selected and ordered around
the left/right exchange. Unused candidate columns remain in the source artwork.

Arms and legs move in depth, with foreshortening and natural occlusion rather
than sideways kicks. A forward-reaching hand may be hidden; it is not drawn
through the coat. Boot soles are visible in trailing/lifted poses. The opposite
contact exchanges the visible trailing hand and lower boot. The complete
drawings include all overlaps; no limb rig, body-part assembly, spatial mirroring
or procedural posing is used.

Sources, selected columns, bounding rectangles, uniform scales, origins and
hashes are retained in `assets/source/characters/iselin/walk_back/redrawn/`.
Technical export performs hard-alpha extraction, one scale per source strip and
whole-drawing registration. Rebuild: `python tools/export_iselin_back_walk.py`.

Checks cover16 distinct RGBA frames, hard alpha, bounds, timing, successful
Pygame loading, and the hand/boot exchange at opposing contacts. The native
sheet was visually inspected for complete silhouettes, costume sides, hand
count, left/right identities and transitions across strip joins. Such checks
support motion review; they do not certify precise joint angles or world-space
foot locking. This remains an in-place animation preview for user approval.

## Right foot correction, revision 2

Audit found the right boot held high through frame 4, then dropping about nine
native pixels into frame 5. Frames 11–12 also had an abrupt height change.
Imagegen redrew complete four-pose strips with smaller right-foot lift and a
more gradual return to contact. Export protects every original pixel outside
x22–31, y48–71, retaining the arms, upper body, and left leg exactly.
No procedural limb translation, rotation, or stretching is used.

The revised right-boot bottom positions are
63, 62, 63, 65, 66, 69, 69, 69, 69, 68, 66, 63, 64, 64, 64, 65.
The largest adjacent change is three native pixels, including the loop seam;
the earlier nine-pixel drop is removed. This measures visible vertical motion,
not physical world-space foot locking. Frame timing remains 35ms.

[Initial preview](initial_preview.gif) and [initial frame sheet](initial_frames.png)
remain available for comparison. Frozen original frames and complete generated
correction drawings are in `redrawn/right_foot_revision/`; source hashes and
registration are recorded alongside the original generation records.
