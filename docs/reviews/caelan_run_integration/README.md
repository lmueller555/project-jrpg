# Caelan HD run integration and retired travel cleanup

All four approved 16×25 ms runs are active through the existing runtime
registry. Every one of the 141 approved HD PNGs is byte-identical to the
pre-integration commit. Only integration metadata and consumers changed.

| Bank | Artwork canvas | Logical draw anchor | Cycle |
| --- | --- | --- | --- |
| Idle / walk | 48×72 | [12,30] | idle / 560 ms |
| Front / rear run | 48×76 | [12,32] | 400 ms |
| Left / right run | 56×76 | [14,32] | 400 ms |

`Player.draw_anchor` follows the selected gait bank. Ordinary-world and regional
overworld drawing both honor it; explicit story anchors/poses retain priority.
Idle/turn/gait reset behavior, running speed 108 world units/s, collision,
interaction geometry and camera coverage are unchanged. No runtime bob is added.

Rescue display actors now load Caelan's current HD idle/walk travel at density 2;
their unique assist/action poses retain their existing density, anchors and cues.
SanctuaryReturn uses current HD walking/running banks while carrying cups, with
its logical four-phase hand guide sampled by normalized cycle time rather than
indexing a sixteen-frame bank with a four-element array. Prop ownership and
pickup/delivery cues remain unchanged. Unique combat, household, seated, casting,
carrying and rescue/support poses have no locomotion replacement and remain
scene-owned assets.

## Removed assets and reproducibility

The user requested deletion of superseded Caelan artwork. Removed 255 files:
old 1× idle/walk/run frames, strips, manifests, redundant old limb/source exports,
travel-only previews, obsolete exporters and tests exclusive to those retired
banks. Git retains the previous versions. The explicit
[retirement ledger](../../../assets/characters/caelan/retired_travel.json) records
paths/hashes and intentional preservation-contract retirements. Approved HD
sprite hashes remain protected. All four run exporters rebuild the integrated
metadata and the unchanged approved pixels successfully.

Source atlases and original prop layers still needed to reproduce unique story
actions remain source inputs. Their source-registration helper cannot export
the retired travel banks. Older terrain/companion review tools explicitly
sample current HD art into their existing logical review canvases through
`tools.caelan_reference`; historical reference names never load or recreate old
travel PNGs. Retired hash references can be checked against the ledger. The
grove, grass, crystal and cave/catalog scale-reference reviews were regenerated
using the current Caelan. Procedural gameplay terrain modules remain unchanged;
only review images and their provenance/catalog records changed.

## Actual gameplay captures

Reproduce with `python tools/capture_caelan_run_integration.py` under the project's
Pygame/Pillow environment. It uses temporary save/settings paths, actual
`Player.update` movement and production world drawing at native density. It
checks real collision rather than removing scenery and asserts unchanged quest
state. Each direction travels for two complete run cycles and then stops.

- [Sanctuary hall travel](hall_travel.gif) / [direction samples](hall_directions.png).
- [Town travel](town_travel.gif) / [direction samples](town_directions.png).
- [Cave travel and lighting](cave_travel.gif) / [direction samples](cave_directions.png).
- [Idle/walk/run transitions](walk_run_transitions.gif).
- [Foreground overlap](tree_occlusion.png).
- [Cup delivery](cup_carry.gif) / [native scene sample](cup_carry.png).

Inspected native scene frames for cast scale, outline/detail retention, padded
anchor placement, lighting, painter depth and scene-prop continuity. The in-place
artwork remains the approved drawings; uneven stylized support travel is still
visible and is not calibrated for perfect world-foot locking.

Loaded player travel surfaces occupy 2,439,680 bytes (about 2.33 MiB), including
logical/native buffers. Frames are loaded once, not resized per movement update.
[Evidence](evidence.json) records movement samples, unchanged quest state,
foreground placement, memory and approved PNG hashes.

## Validation

The focused run passed 76 tests covering every run-frame boundary and wrap,
native pixels and padding, gait/story anchor priority, stopping, blocking,
turning, diagonals, removed-bank absence, existing walk preservation, contours,
speech placement, social interactions and grove reproducibility. Related scene
and rendering tests cover rescue, cup delivery, pickup, Venn actions, party
travel, compositor behavior and quest UI. Their retired mill reference was
updated to the scene-owned body input and its corrected test passes.

The broad suite is **not green** and was stopped after unrelated failures.
A separate worktree of unchanged main (`fcd89869`) reproduced 8 failures and
8 errors in a 53-test sample, including existing doctrine/dialogue, encounter,
and battle UI expectations. These systems were not changed to force a pass.
[Validation details](validation.json) record the sample and focused results;
this review does not claim that all 3,139 discovered tests completed.

An additional 36 asset-cleanup tests pass: cave/catalog deterministic rebuilds,
retired source provenance, Sanctuary art and grass occlusion across every run
frame. The grass pixel tests project from the selected bank anchor rather than
the retired fixed anchor.

Changed Python modules compile, manifests parse, all retired files are absent,
all approved HD PNGs match the previous revision exactly, and whitespace checks
pass. The canonical [Caelan runtime guide](../../../assets/characters/caelan/README.md)
and [visual standard](../../VISUAL_ART_STANDARD.md) describe current integration.
