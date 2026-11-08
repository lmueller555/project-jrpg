# MQ03 emergency worker

The source recipe derives an injured Crown worker from the approved `male_03`
native sprite and portrait. Original source files remain unchanged and their
hashes are verified. The same existing face and clothing material are retained,
with dust, a small forehead dressing, a forearm wrap and a guarded posture.
The portrait raises the brows and parts the lips to communicate shock and
shortness of breath.

Every walking pose remains 24 × 36 with draw anchor `(12,30)` and an 8 × 4
physical foot probe. The lower boot-contact rows are preserved exactly from
each original directional pose. Repeating the hurt-side support frames gives
the ordinary `StoryActor` a longer uneven limp without moving its root or
inventing another movement controller. The quest owns the physical route from
the courtyard through the real hall door and into the dining room.

The pack also exports an alarm pose, a seated resting pose aligned to the
existing spare bench, and a small cloth-preparation pose for Serene. Action
cues `survivor_alarm`, `lucan_disbelief` and `survivor_aid` remain transient:
they never commit story progress or change physical actor positions.

Build with `python tools/build_regent_emergency_assets.py`; add `--check` to
verify all checked-in exports without writing. The normal social portrait
registry points to the new derivative `regent_survivor.png`, and the visit art
registry adds the `regent_survivor` actor. The existing visit builder preserves
that registration and the later emergency room stations when rerun.

`materials_review.png` compares native directional poses with Caelan, the
unequal walk cadence, portrait and registered resting/alarm poses.
