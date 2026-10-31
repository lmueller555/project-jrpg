# Authored bridge surveyor / tea tender

The bridge tender uses the same gray-haired, slate-shirted, brown-trousered
`male_03` identity as the grain coworker. The existing generic NPC sprites and
all grain coworker exports remain read-only.

`cup_walk_generated.png` contains sixteen whole-body directional cup-carry
frames. `actions_generated.png` supplies planted cup holds, pickup, offer /
receive and measuring poses. Both are original, retained transparent image
generations; their exact prompts are stored alongside them. `identity_reference.png`
records the existing four-direction appearance. Generations also referenced
the authored grain coworker sheet to maintain its compact proportions.

The cup stays in the same anatomical right hand: image-left in front view and
image-right in back view. Rear cup rendering occurs behind the torso, with its
outboard edge visible beside the bent right arm. `cup_alignment.png` shows the
actual existing 6×6 cup on the registered body poses for all directions.

`tools/build_bridge_tender.py` crops complete figures, thresholds alpha and
nearest-scales each clip uniformly to the same standing height. Walking uses
the head/torso axis for horizontal registration; changing shoe bounds cannot
drag the entire body or cup sideways during a stride. Stationary actions use
sole registration to preserve their authored hip hinge and reach. No individual
limb is drawn, rotated, stretched or replaced.

The short pickup uses the close grasp poses because the kettle tray is already
at waist height. The source's far-reaching alternatives stay unused. Similarly,
the offer uses the natural half reach rather than the most extended arm.
Actual palm contacts determine the runtime docking positions: the tender stands
four pixels nearer the support tray, and that tray moves three pixels left and
down. This lets the cup touch the original wobbling stone and then the steady
tray without sliding feet or floating past an unchanged hand.

Cup/tool offsets and palm contacts are explicit manifest metadata. The cup and
tool remain separate controller-owned props; no duplicate object is baked into
the sprite. Only states used by this character's actual routine are included;
the tender does not receive the mason's seated/drinking animations.

Left measuring and front rest copy the already-authored grain coworker frames
byte-for-byte, with source hashes retained. This is safe reuse of the same
person's full body, not reuse of the obsolete procedural front-facing arms.

`native_review.png` and `action_review.gif` are reproducible inspection aids.
The final bridge gameplay capture verifies object handoff, safe tray contact,
blocked carrying, direction changes and persistence with the real controller.

```sh
python tools/build_bridge_tender.py
python tools/build_bridge_tender.py --check
```
