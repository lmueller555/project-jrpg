# Tomas's sanctuary work poses

`tools/build_tomas_routines.py` assembles the approved directional body parts
and shared walking phases with new authored three-joint sleeve poses and small
work props. `poses.json` retains the emitted pose coordinates and prop anchors.
The builder is the editable source; approved idles/walks remain read-only.

The extra 64×48 frame area holds the adjacent tabletop model and hands; the
character is still registered from a 24×36 body with `[12,30]` scene anchor.
The padded canvas uses body offset `[20,6]` and draw anchor `[32,36]`.
Props and hands retain hard alpha and native pixels. Joint lengths are bounded;
there is no scaling of limbs or heads. The new carry variants preserve the
original legs, torso, knee patch, head/shoulder bob and 140 ms frame timing.

The dining-room map reuses the approved cottage table and adds one small box.
`collision_with_tomas.png` is rebuilt from the untouched `collision.png` plus
the two furniture footprints. Runtime identity, random rests, surface ownership,
door transitions and dialogue interruption are covered by the Tomas tests.
