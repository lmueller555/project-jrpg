# First household and temporary escort

Accept Serene's request after breakfast. Tomas joins Caelan after the follow-up
conversation and follows through the existing doors. Use **M** to locate Halden's
cottage on the eastern mill terrace. Approach Halden inside to start the approved
dialogue; click anywhere to advance. Finish it to hand over his medicine.

At the three grain sacks by the entrance, **E** picks up either outer sack.
Carry it to the corresponding space on the wooden pallet near the north wall;
the **E: Set sack on the dry pallet** prompt identifies the unloading position.
At the middle sack, **E** asks Tomas to help. Give him room to approach: he lifts
it from the other side and carries it to storage. His task waits safely if Caelan
stands in the route. Caelan and Tomas can carry their respective sacks at once.

After 3/3, approach Halden for the approved completion exchange. Then approach
Tomas for his goodbye. Halden's objective finishes when Tomas actually leaves
through the cottage doorway. Elira and the Venn family become available in
either order. Their practical errands remain future work. Tomas walks back to
the sanctuary and resumes preparations.

## Runtime ownership

`HaldenVisit` borrows the existing persistent Tomas; no duplicate is spawned.
His ambient scheduler pauses only while the visit owns him. Escort movement
uses a trail roughly one tile behind Caelan, pixel-checked local paths and the
same door open/close sensors as other residents. A scene graph supports multiple
door transfers even if the player moves ahead. A coarse long-distance route
checks every two pixels of every edge for the sanctuary return. Blocked routes
wait and retry; they never cross collision or teleport to recover.

The escort's feet yield rather than block Caelan. Other NPCs remain solid.
Scripted dialogue uses the existing live portrait bubbles and click controls.
Leaving unfinished prose cancels its callback; it never consumes medicine,
finishes a conversation, or completes the objective. Only the short physical
gestures own Caelan's movement. Pause and inventory freeze those gestures too.

Props have one owner at a time: entry, Caelan, Tomas or pallet. Contact frames
transfer that ownership; room props sort with the existing furniture. Medicine
uses the protected inventory delivery API at its handoff beat. The medicine
receipt does not complete the sack task.

## Checkpoints and art

The optional `halden_visit` save record has its own version and validation.
Stored sack IDs, Caelan's carried sack and the closing/goodbye facts persist.
Tomas's interrupted carry restarts safely at the sack's entry rather than losing
it; its successful set-down is checkpointed. Medicine cannot be granted twice.
Malformed progress or a sack task without a medicine receipt is rejected before
loading. Older saves remain supported. New Game clears local task facts.

`tools/build_halden_visit.py` exports Halden's four-direction costume from the
shared male template, the sack/pallet/bottle and registered carrying poses using
Caelan and Tomas's approved four-frame walks. Existing approved art is unchanged.
The generated portrait master is retained in `assets/source/portraits/eldenmere`;
`tools/export_dialogue_portraits.py` also exports its 72×72 runtime portrait.

`tests/test_halden_visit.py` exercises real movement, input, collision, door
following, medicine timing, sack ownership, visible Tomas assistance, delayed
unlocking, reloads, old saves and the return route. The wider suite covers the
sanctuary opening, proximity dialogue, inventory, NPC routines and UI.
