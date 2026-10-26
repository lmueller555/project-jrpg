# Elira's memorial lantern

Finish Halden's visit and Tomas's goodbye first. Elira's cottage is near the
southern bridge; **M** opens the town map. Enter and approach Elira to start her
approved exchange with Caelan. Click anywhere to advance. Finishing that exchange
passes her the food and lamp oil, removing her supply bundle from inventory once.

Walk to the stool beneath the high shelf. **E** aligns Caelan on the clear
approach, steps him up, raises his hands and carefully lifts the unlit memorial
lantern. The shelf switches to its approved empty state at the contact beat.
He lowers the lantern and steps down. Walk to the north side of the dining table
and press **E** when prompted to set it on the tabletop. Approach Elira again
for the approved conversation about her husband, remembering him and the festival.
The Elira objective completes only after its last line has been read.

Venn remains independently available. If Venn was already completed, the quest
becomes ready for Serene's report, without automatically reporting or turning in.
The Venn repair is now playable; the staged mill-failure end of MQ01 remains next.

## Ownership and animation

`elira_visit.py` registers one named Elira in her existing cottage. Her four
directional idles share the approved female silhouette, with a silver-streaked
low bun, hazel eyes, mulberry dress, oatmeal apron and sage shawl. Her portrait is
exported at 72×72 from the retained generated master. Existing NPCs and approved
room artwork are unchanged.

The lantern has exactly one saved location: `shelf`, `carried` or `table`.
The existing shelf full/empty sprites and stool are reused. Caelan's pose canvas
provides room for the existing lantern; his body keeps its original native pixels
and approved walk timing/bob. Two six-pixel arm segments pivot during the reach
and lowering poses. The first held lantern uses the shelf's exact world origin;
its rendering stays behind Caelan where his body should obscure it. The final
tabletop sprite sorts above the table, with its base resting on the wood surface.

Only the brief handoff, retrieval and placement gestures own player movement.
The world keeps running. Dialogue uses live portrait bubbles, and walking away
cancels unread prose without granting completion. Pause and inventory freeze
gestures. Logical feet remain on the valid stool approach while visual poses
represent stepping up; climbing never edits collision or permits free movement
through the stool.

## Checkpoints and compatibility

The optional `elira_visit` save record has its own version and strict validation.
Inventory separately records the supply receipt. A carried/table lantern without
an unlocked visit and a supply receipt is rejected before loading. Interrupted
retrieval resumes on the floor: before contact the lantern stays on its shelf,
and after contact Caelan holds it. Placement persists at its contact beat. Leaving
with the lantern is safe; returning can finish the same visit without duplication.

Older saves without this record retain their quest facts: outstanding visits
start with the lantern on the shelf, completed visits put it on the table. New
Game resets the shelf, supplies and local progress. Completed visits use a short
follow-up line and do not replay rewards, handoffs or the memorial conversation.

`tools/build_elira_visit.py` rebuilds the costume and registered poses.
`tools/export_dialogue_portraits.py` also exports Elira's portrait.
`tests/test_elira_visit.py` covers real doors/movement/input, exact shelf contact
pixels, item consumption, interruption/reload boundaries, pause, prerequisite
gates, both household orders and delayed objective completion.
