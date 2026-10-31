# Authored grain coworker actions

`work_generated.png` is the retained, unmodified transparent image generation.
It contains sixteen whole-body poses of the gray-haired, slate-shirted,
brown-trousered `male_03` worker. `identity_reference.png` is a nearest-scaled
contact sheet of his existing front, left, right and rear idles; those original
sprites remain unchanged. `prompt.txt` records the generation brief.

The action sheet authors complete figures rather than drawing new arms onto a
front torso. Cart work faces left. Shared support and lowering face right.
The crouch lowers the hips and knees with ordinary limb lengths. Rest uses a
small shoulder roll with hands near the waist.

`tools/build_grain_coworker.py` exports these whole frames at one uniform 1/8
scale, thresholds alpha and registers each pair of soles to `[20,38]` on a
40×44 canvas. It does not repaint, rotate or stretch limbs. The weighted high
hold uses the best stable authored frame instead of playing alternates whose
hands drift. Lowering starts with that identical hold, then uses the authored
half-squat, low squat and release. Front rest plays once and holds its last
frame. A separate 400ms recovery reuses the released crouch, half-squat and
upright authored figures before walking away. Its frames own no sack attachment;
the grounded sack stays in place as the body rises. Directional walking and idling continue to use the approved generic
worker sprites without modifications.

The sack and cloth are separate runtime objects. No props are baked into the
body frames. Manifest hand contacts refer to visible palm pixels; runtime
coordination uses these contacts rather than nominal offsets that would force
unnatural arm extensions. In particular the high far palm is `[9,-14]` and the
low far palm `[11,-5]` relative to the worker's feet. These touch different
points along the external sack's left edge while it is lowered.

`native_review.png` and `action_review.gif` are reproducible native-frame
contact and motion previews. Production shared-grip and cart registration are
reviewed in the region NPC gameplay capture.

```sh
python tools/build_grain_coworker.py
python tools/build_grain_coworker.py --check
```
