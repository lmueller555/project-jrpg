# Elden Vale landmark framework: disposable actual-game review

PR 1 establishes rendering/build contracts only. **No production landmark scenery
is activated.** These are initialized `Game` captures at native 960×640, with
in-memory fixture metadata and disposable settings/saves. Starts and composition
views are explicitly positioned; subsequent span traversal uses `Game.update`.
This is not an uninterrupted quest playthrough or a final placement approval.
The technical placement plan is maintained in [OVERWORLD](../../OVERWORLD.md#signature-landmark-framework-and-cross-scale-placement-plan).

## Renderer evidence

- [Local cutaway](regional_local_cutaway.png), [story-position override](story_position_cutaway.png)
  and [reduced motion](regional_reduced_motion.png) show restrained immediate
  visibility assistance around the actual sprite position. Isolated overhead
  pixels are time-invariant under reduced motion.
- [Walking/running both directions](span_walk_run.gif) uses actual gameplay
  beneath a disposable lintel. It is not the finished arch/support assembly.
- [Companion cutaway](detailed_companion_cutaway.png) uses a real passive Mira
  follower in a temporary-recruitment fixture; 60 further movement updates check
  both full-foot player/follower positions. No production roster changes persist.
- [Offscreen-origin branch](offscreen_origin_visible_branch.png) exercises a
  784×528-logical drawing whose origin lies 560 units left and 190 above the
  camera. Its visible branch survives full-bounds culling.
- [Native lintel detail](lintel_native_detail.png) matches the source's RGBA
  render pixels exactly, including its half-unit logical registration: **zero
  mismatches**, without enlargement of the logical mirror.
- [Town distant fixture](town_distant_fixture.png) places antler tips behind the
  existing hall roof, using a fixed world anchor rather than player-relative
  parallax. It is a screening test, not final regional skyline composition.

Pause and focus loss preserve elapsed time, player position and exact world-only
native pixels **while under the fixture span**, then exploration time resumes.
Save/Continue beneath the span preserves exact quests, party, dialogue flags,
player and regional state, with one owner per sampled town actor. The disposable
landmark registry requires no new save fields.

## Placement study and selected direction

The unmodified detailed support study is intentionally shown as a rejected final
composition: [southern viewpoint](detailed_study_skull_glimpse.png),
[eastern loop](detailed_eastern_loop.png), [northern loop](detailed_northern_loop.png).
Full-scale ground-pass skull artwork causes the player to appear on bone in the
north; the old southern view crops almost all skull. A safe declared support
rectangle does not establish finished depth or camera composition.

The selected **0.625 coherent build-time rendition** is demonstrated by disposable
whole-master projection and exact even-pixel segmentation:
[northern loop](projected_northern_loop.png), [cave apron](projected_cave_apron.png),
[old southern view](projected_skull_glimpse.png). Its master is 490×330 logical at
`[726,-41]`, contact `[948.5,274,45,12.5]`. The northern loop reveals anatomy at
ordinary camera coverage; the cave apron remains clear. PR 2 must finish the
lowest rubble/root fringe's registration to existing solid ridge, raised-skull
cutaway on the eastern circuit, and essential grounding dressing. It must not
silently activate these diagnostic fixtures as final production metadata.

## Budgets, reproducibility and scope

`observations.json` records exact source/capture hashes, fixture coordinates,
movement traces, preserved states and cache/timing measurements. The harness
rejects tracked runtime/map/manifest changes during a run. The large-source probe
uses 240 distinct camera positions and asserts the source LRU remains within
16 MiB. Working surfaces are viewport-bounded and not retained per position.
Recorded timings cover **only landmark drawing**, excluding simulation, display
and UI, on SDL dummy; they are not an overall frame-rate guarantee or a direct
step-1 whole-world benchmark.

```sh
python tools/capture_landmark_framework.py
python -m unittest discover -s tests -p 'test_landmark_layers.py' -v
```

Existing regression suites/build checks are reported separately in the PR.
PR 2 still owes final cross-scale activation, protected circuit/story/door/cave
review, support/collision agreement and production rendering budgets. PR 3 still
owes actual complete arch support clearance and full causeway travel. Rising
Rain, associated routines/actions and final atlas artwork are not included.
