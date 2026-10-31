# Elden Vale NPC sprites and routine animation

The opening overworld contains six NPCs: the loader and coworker at the western
grain farm, and two road guards at each of the northern and southern checkpoints.
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
release use the same registered contacts as lifting.

The sack and cloth remain separate props. Their real position and draw order
follow the active body's attachment data, including appropriate occlusion on a
rear view. The shared lift registers both workers' palms around the same sack.
Cart placement includes the short supported adjustment needed to reach the
second slot without extending the worker's arms unnaturally.

The delivery still has exactly three sacks and two completed cart placements.
The third sack is visibly lifted before the optional exchange, then lowered
with help. Existing mill gating, dialogue, completed beats, blocked-path
behavior and safe Continue reconstruction remain in place. The save version
and `overworld.grain_farm` durable fields are unchanged.

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
- The original worker prototype reference remains available for history.
- `tools/build_grain_workers.py` invokes the two authored role exporters and
  verifies the unchanged sack/cloth sources. The former arm assembler and its
  obsolete flat pose files are retired.

```sh
python tools/build_grain_workers.py --check
python tools/build_road_guards.py --check
python tools/capture_region_npcs.py
```

The [production review](reviews/region_npcs/README.md) includes native-scale
animations, close views, matching portraits, complete work routines and
persistence/obstruction checks. See [the overworld guide](OVERWORLD.md) for
regional travel and the grain delivery's durable state.
