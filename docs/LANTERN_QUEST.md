# Liam’s lantern quest — PR1 through PR4

This guide owns MQ04 controller, object, actor, and save behavior. The
[consolidated MQ04 script](narrative/game_01/CH01_MQ04.md) owns the complete
authored story, dialogue, character boundaries, and four-part route.

## Committed segment endpoints

| Part | Checkpoint | Completed objectives | Quest status |
| --- | --- | --- | --- |
| 1 | `frame_ready` | First two | Active |
| 2 | `elira_visited` | First four | Active |
| 3 | `serene_heard` | First six | Active |
| 4 | Final acknowledged farewell | All eight | Complete |

Earlier segment endpoints describe their local state, not missing continuation.
MQ04 stays on the preparation day; MQ05 and the festival remain separate work.

## Dialogue and presentation

`assets/story/lantern/scene.json` contains nine main scenes: `invitation`, `classroom`, `design`, `permission`, `workshop`, `test_shape`, `assemble`, `lift` and `frame_ready`. `walk_chat` is optional. Short repeat replies are selected by committed progress; later craft facts must not appear before the player has reached them.

The complete speaker-attributed transcript is [CH01_MQ04](narrative/game_01/CH01_MQ04.md). All nine main exchanges are player-paced. Canceling or leaving one cannot commit unread consent, construction or success.

`assets/story/lantern/village_scene.json` adds eleven main exchanges: `departure`, `mill_arrival`, `mill_flour`, `venn_arrival`, `venn_preparations`, `elira_welcome`, `elira_lantern`, `elira_memory`, `elira_company`, `elira_goodbye` and `reflection`. The [PR2 transcript](narrative/game_01/CH01_MQ04.md#part-2) includes every speaker-attributed line and optional reply. Walking conversations after the mill and Venns are optional, and earlier visits use replies that do not reveal later events.

`assets/story/lantern/rest_scene.json` adds eleven main exchanges: `break_invitation`, `collect_frame`, `home_welcome`, `snack`, `paper_practice`, `brothers`, `liam_questions`, `sanctuary_welcome`, `returning_life`, `remembering` and `sanctuary_close`. The [PR3 transcript](narrative/game_01/CH01_MQ04.md#part-3) includes all speaker-attributed dialogue and repeat replies. The father uses his existing family identity and appearance; his personal name remains unassigned. Optional replies respect the materials’ current location and do not complete an objective.

`assets/story/lantern/finish_scene.json` adds twelve main exchanges: `finish_invitation`, `home_return`, `purpose`, `final_panel`, `dry_fit`, `fasten_covering`, `finished_lantern`, `school_welcome`, `show_mother`, `homeward`, `put_away` and `farewell`. The [PR4 transcript](narrative/game_01/CH01_MQ04.md#part-4) includes every speaker-attributed line and solo repeat reply. Main dialogue has 206 lines and 1,395 words; the comfortable 10–15-minute conclusion is a playtest target, not a measured duration. Later replies do not claim that Mira, Elira or Serene has seen a finished lantern that the mandatory route never showed them.

The drawing, material pieces, partial frame and finished frame make the work visible. One lantern state follows the work; a held and resting copy must not appear simultaneously. Craft poses preserve the approved idle bodies and believable limb lengths, with contact points registered to the materials. The frame is tested for balance without fire.

## Progress and save continuity

| Segment | Controller owner | Save contract |
| --- | --- | --- |
| Opening frame | `lantern_quest.py` | Establishes the version-one committed-stage record and full objective sequence. |
| Village visits | `lantern_village.py` | Extends version-one progress with village checkpoints and original resident ownership. |
| Home break and Sanctuary | `lantern_rest.py` | Extends version-one progress with material pickup, home and Sanctuary checkpoints. |
| Finishing and return | `lantern_finish.py` | Extends the same record with final actions, acknowledgment and persistent placement. |

`QuestLog.complete_and_turn_in` commits the final objective and completion
atomically, producing one notice and one save. There is no intermediate
ready-to-report state or additional report to Tomas.

The quest definition establishes the full objective sequence from PR1, so later segments can extend the same active quest without migrating an already completed short placeholder. MQ03 completion makes it available; reading the invitation accepts it. Finishing PR1 commits `frame_ready` while keeping later objectives outstanding.

PR2 extends the committed scene stages along one authored route. Existing PR1 saves continue at their saved checkpoint without replaying the school or frame work. Reaching a location does not complete its conversation; `visit_neighbours` waits for the completed Venn preparation exchange, and `visit_elira` waits for the farewell and outside reflection. The saved world continues to show the unlit frame and drawing at Mira’s table, the working mill, repaired irrigation and Elira’s same memorial lantern.

PR3 adds explicit pickup, home and sanctuary checkpoints rather than falling back to workshop staging. Material ownership follows the committed sequence: workshop → carried → home. Reloading an interrupted handoff or placement restores the last committed ownership, with one frame and drawing. Carry art follows Liam’s actual direction and movement; a fixed lift pose must not slide through travel. The home practice uses a separate loose sheet while preserving the real frame for the final segment.

PR4 continues from `serene_heard`, preserving all earlier committed facts. The finish actions and inspection are separate from the mother’s acknowledgment and final placement. Covered-lantern ownership follows home → carried to school → carried home → resting at home. Only the lantern travels on this last route; the drawing and practice paper stay home. Interrupted scenes restore the last safe checkpoint, without duplicate held/resting copies or premature credit.

At the end, `show_mother` and quest completion commit together after the complete farewell; an active save with all objectives complete is not a valid intermediate endpoint. The live ending releases borrowed actors through normal ownership handoffs rather than resetting the world. Completed saves restore the finished lantern at home, the mother at the school, Serene in the hall, Tomas at his preparation station and Liam’s ordinary home behavior. They do not replay the completion notice or begin MQ05. New Game remains the explicit reset to opening routines.

`lantern_quest` stores versioned committed story progress. Dialogue cursors, partial animation clocks and path caches are transient. Restore reconstructs the appropriate actors, props and safe scene checkpoint. A newly gated MQ04 may be absent from older saves; completed MQ03 saves gain access without replaying the regent’s visit or its announcements. An active MQ04 requires matching valid story facts. New Game releases quest ownership and restores the ordinary opening routines.

The controller takes over Tomas only after MQ03 has released his staging, and coordinates Mira’s existing post-mill behavior. Liam’s block-building or shared Daisy routine must settle safely before the quest borrows him; the same actor’s location tracking stays accurate through doors. The mother and other children are borrowed from their existing home actors, not duplicated as classroom residents.

## Validation and review

Verify the complete segment using normal interactions, collision-aware movement and real door transfers. Cover cancellation and reload at each committed milestone; repeated interactions; active Liam/Daisy and block activity at handoff; actor identity across rooms; clear classroom, threshold and workshop approaches; no premature objective credit; and a clean New Game reset. Earlier quest outcomes, including the working mill and released Venn cart, must remain intact.

Review captures should show the actual game’s classroom, outing, workshop and visible frame, with readable dialogue stills. The complete game suite is required because character ownership, story handoffs and saves cross existing systems. Recorded test and capture results belong with the review artifacts, not as unverified claims in this guide.

For PR2, additionally verify continuation from a real PR1 save; scene cancellation and reload at every new checkpoint; original resident identities; companion passage through both cottages; Mira’s return to her registered workbench; no duplicate drawing or lantern; and the active four-objective endpoint. Capture the route from the actual frame checkpoint through the normal mill path, cottage doors and final outside exchange.

For PR3, additionally verify continuation from the real PR2 endpoint; every conversation and object handoff across cancel/reload; one material set in workshop, transit and home; four-direction carry registration; safe placement; Liam’s visible paper activity during the brothers’ dialogue; Daisy’s eating, resting and held-bone states; and Serene’s explicit handoff from MQ03. Earlier flour, decoration and repair states must persist beyond the village section. New Game releases the borrowed family and sanctuary staging. Review the actual route, home and sanctuary scenes alongside the carry/craft pose study.

For PR4, additionally verify continuation from `serene_heard`; all four finish actions and their acknowledged dialogue boundaries; final covering, inspection and directional carry; school actor identities; the mother’s completed exchange without premature quest completion; safe home placement; and one final completion notice only after farewell. Cover cancellation and reload at each new checkpoint, completed-save restore, repeat replies and New Game. Walk the complete MQ04 route through all four segments without replacing the intermediate state with test seeds, while preserving earlier repairs, flour and decoration facts. Capture the real home work, school acknowledgment and final resting lantern.

## Chapter continuity

MQ04 happens on the preparation day and MQ05 on the next day. The broader [chapter structure](narrative/game_01/CHAPTER_01.md) now contains five main quests. The festival’s detailed activities and inciting event remain later work. The authorization letter remains the planned post-festival escalation, while the excavation catastrophe belongs to Chapter 3. In-world religious belief remains distinct from established physical rules and from the Crown's undisclosed investigation; this quest does not reveal the harvesting network or its military purpose.
