# Elden Vale NPC sprites and routine animation

Character–object work follows the mandatory
[global interaction standard](OBJECT_INTERACTION_STANDARD.md) and its
[personal-prop visibility companion](PERSONAL_PROPS.md). Local coordinates,
contact timings, and captures below describe the current implementation.
Natural proportions and readable intent take priority over exact hand contact;
a small, deliberate transfer snap is acceptable.

The opening overworld contains ten human NPCs: the loader and coworker at the western
grain farm, the mason and surveyor at the ruined western crossing, and two road
guards at each of the northern and southern checkpoints, plus the kitchen
gardener and orchard picker.
Their animation belongs to the persistent region actors, independently of the
streamed terrain chunks.

## Grain workers

The loader retains the rust/charcoal `male_02` appearance; the coworker retains
the slate/brown `male_03` appearance. Their existing approved four-direction
idles and walks are reused unchanged. Authored full-body work sequences supply
the profiles, rear views and poses needed to handle grain, cover the stack,
place a load, check lashings, share a grip and recover to rest.

Each role uses a 40×44 transparent canvas and foot anchor [20,38]. Its
`assets/characters/grain_workers/<role>/animation.json` registers frame timing,
looping, palm contacts, sack attachment and depth. Bodies are uniformly
registered to a common scale. A crouch lowers the body through the hips and
knees; it does not resize the limbs. The action exporter retains the original
generated frames and registration recipe.

`grain_farm.py` selects carrying and holding frames by the worker's actual
facing. An obstructed route holds the load steadily and resumes the walking
cycle after the path clears. Work sequences start at their own action boundary;
ordinary idle and walking loops keep a continuous gait. Reversible lowering and
release preserve the authored body motion.

The sack and cloth remain separate props. A sack stays at its source until the
grab animation finishes, then snaps to the worker's holding attachment. It stays
held throughout placement or shared lowering, then snaps to its destination.
There is no intermediate floating or cart slide. Held sacks follow directional
holding attachments and draw behind the body on rear views.

The delivery still has exactly three sacks and two completed cart placements.
The third sack is visibly lifted before the optional exchange, then lowered
with help. Existing mill gating, dialogue, completed beats, blocked-path
behavior and safe Continue reconstruction remain in place. The save version
and `overworld.grain_farm` durable fields are unchanged.

## Bridge crew

The mason retains the moss/tan `male_01` appearance and the surveyor retains
the slate/brown `male_03` appearance. Their own authored manifests live under
`assets/characters/bridge_workers/<role>/`. Work, measuring, stone carrying,
cup carrying and handoff use the direction appropriate to the object and route.
Full-body seated and recovery poses keep the mason supported by the bench while
his cup moves between his hands and mouth.

Stones stay in the source pile through the full lift and remain held through
placement, snapping only when each action completes. Cup pickups, supported
set-downs and handoffs likewise change ownership only after the action completes;
the stone wait, retrieval and tray placement are separate actions.
Ordinary carrying, drinking and tool motion retain their authored action and
holding positions. Existing painted contacts are local registrations; exact
pixel contact is optional when the action remains believable.
The mason steps
into reachable placement and receiving stations; the cup has one owner and one
visible location through the shaky-stone, steady-tray and handoff sequence.
Holding a cup or stone on a blocked path uses an authored still hold.

The crew still sorts exactly three stones and offers the same optional tea
break. Existing `overworld.bridge_crew` fields (`sorted`, `tea_beat`,
`request_read`, `greeted`) retain their meanings. An optional `cup_phase` records
completed cup transfers so Continue preserves the owner and does not replay a
completed placement. Older records derive a safe phase from their existing beats.
Sorting and tea do not repair the bridge, open a checkpoint or alter quests.

## Garden, orchard and sheep-care props

The watering vessel, turnips, optional relocated plant, three apples and borrowed
sheep-care basket stay at their source for the complete grab animation. During
set-down they stay in the worker's hand until the animation finishes, then snap
to the destination. Pickup and placement sounds occur at that same boundary.
Filling, watering, admiring fruit and ordinary carry motion remain animated.

All held props use regional depth sorting and the actual camera view. Rear
views place the prop behind the body's opaque silhouette; exposed portions
remain visible. Front, side, and oblique views use the appropriate near/far
arm and object layers, as required by the global standard. Placement must respect
the receiving basket's support and rim depth. The sheep-care basket's collision
footprint changes with
its completed pickup or placement, not when the animation begins.

`tests/test_regional_prop_transfers.py` checks action boundaries, save/Continue,
single ownership, collision and pixel-composited rear-facing occlusion.

## Checkpoint guards

The guard sprites and portrait share a closed-visored silver helmet and armor,
gold trim, navy tabard, brown boots and a shield on the physical left arm.
Authored front, rear and side views preserve the equipment's handedness.
Small stationary motion and conversational gestures suit their checkpoint duty.

The closest guard becomes the actual speaker. He turns toward the player's
approach for the conversation, holds that direction, then returns to his watch
when the exchange finishes or is canceled. The portrait uses the same guard
identity. Guard feet, collision probes, checkpoint geometry and clearance rules
remain unchanged; a conversation does not open a road.

## Source, rebuild and review

- Worker sources: `assets/source/characters/grain_workers/loader/` and `coworker/`.
- Guard sources: `assets/source/characters/road_guards/`.
- Bridge crew sources: `assets/source/characters/bridge_workers/mason/` and `tender/`.
- The original worker prototype reference remains available for history.
- `tools/build_grain_workers.py` invokes the two authored role exporters and
  verifies the unchanged sack/cloth sources. The former arm assembler and its
  obsolete flat pose files are retired.
- `tools/build_bridge_workers.py` likewise invokes the mason and surveyor
  exporters and verifies the unchanged bridge-work props.

```sh
python tools/build_grain_workers.py --check
python tools/build_bridge_workers.py --check
python tools/build_road_guards.py --check
python tools/capture_region_npcs.py
```

The [production review](reviews/region_npcs/README.md) includes native-scale
animations, close views, matching portraits, complete work routines and
persistence/obstruction checks. See [the overworld guide](OVERWORLD.md) for
regional travel and the grain delivery's durable state.
