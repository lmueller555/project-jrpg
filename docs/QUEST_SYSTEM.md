# Quest feedback and progress

The quest layer provides availability, explicit acceptance, objective updates,
ready-to-report state and completion. The opening assignment is available from
Mother Serene after the opening breakfast; its household task implementations remain future work. The
approved story order remains in `narrative/game_01/CH01_MQ01.md`.

## Player controls

- Approach Serene while facing her to speak. Her gold `!` appears overhead and
  at the sanctuary entrance on the town map, including when she moves rooms.
- Advance prose by clicking anywhere, Space or E. At the response prompt only
  clicking **I'll help** accepts; **Not just yet** leaves the quest available.
- Conversations use portrait speech bubbles above the current speaker, including
  Caelan's replies. Movement, camera tracking and other NPC routines continue.
  Walking away or entering another room closes unfinished dialogue without
  accepting an offer, completing a report or setting conversation flags.
  Response buttons follow the bubble and remain clickable after camera movement
  or window resizing; advance keys and clicks outside them never choose for you.
- Use **J** for the journal. J or Escape closes it; wheel, arrows and Page Up/Down
  scroll. Movement, dialogue triggers and room entry are suspended while open.
- The tracker follows the next eligible objective. Completed objectives gain
  checkmarks, queued ones stay distinct, and `?` replaces `!` when reporting is
  available. Reading Serene's final report page completes a ready quest.
- Acceptance and completion banners include the quest title; objective notices
  name the work finished. Chimes obey the independent effects setting and
  missing audio hardware does not prevent play.
- Escape opens a modal pause menu outside the journal/map. Resume preserves
  the exact scene/page/action; Settings shares music/effects levels with the
  title screen. Quit is an explicit menu choice that checkpoints the journey.

## Title-screen quest playtests

Choose **Quests (Playtest)** on the title screen. All four registered starts
are available without a saved journey or story unlocks. Mouse, arrows/WASD,
Home/End, Page Up/Down and wheel browse the same accessible catalogue controls
as Gallery; Enter or a click starts the highlighted quest.

| Quest | Starting state |
| --- | --- |
| CH01_MQ01 - A Day Like Any Other | Home, before Serene's assignment; approach her normally to begin the offer |
| CH01_MQ02 - A Little Trouble at the Mill | Mira's workshop, before accepting her outing |
| CH01_MQ03 - The Regent's Road | The opening arrival cinematic, before accepting the visit; the quest ending remains in development |
| CH01_MQ04 - A Light of His Own | Home, before Tomas's invitation; uses the supported completed-visit setup only inside this temporary run |

Earlier quest prerequisites are prepared, not replayed. The selected quest stays
available with no completed objectives, and later quests remain locked. Earlier
Venn work uses borrowed tools without forcing the optional failed spell. Starts
after MQ02 include the current mill repair, cups on the table, Blue-focus
gearblade, Aether Edge, and the Boar's actual drops and EXP. Mira is already
recruited, available and active alongside Caelan in these playtest checkpoints,
including when the tester heads straight to the cave. MQ03's ordinary rejoin
conversation still establishes the required Sanctuary party event.

Starts after MQ03 additionally grant **5,500 EXP each to Caelan and Mira**, on
top of their Boar EXP. This fixed cave allowance includes the tutorial and boss
EXP; boss receipts and item rewards do not add further EXP. The later checkpoint
assumes both optional focus guardians were defeated: Aqua/Flame/Ice Edge are
learned, Blue/Red/White focuses are installed, both focus receipts/items and the
Vespermaw receipt/material drops exist, all three bosses are cleared, and prior
acquisition dialogue is acknowledged. Optional treasure containers remain
unopened. Starting MQ03 itself leaves all these cave discoveries unfinished.

Levels and stats follow accumulated EXP; there is no level-one override. Both
available characters start rested at their resulting maximum HP/MP. Later
combat awards EXP and handles level-ups normally. No future companions receive
recruitment or EXP from these checkpoints. Restart builds a fresh checkpoint,
so the Boar reward and cave allowance never stack across restarts.

Runs use the normal gameplay controllers and input, not Gallery's restricted
scene playback. The toolbar identifies **PLAYTEST** and **not saved**:

- **F10 / Restart:** discard the entire run and rebuild its original quest start.
- **F9 / Quests:** discard the run and return to the same catalogue selection.
- **Escape:** the ordinary pause menu; Restart Quest and Quest List are also
  present there. Toolbar controls remain usable during combat and cinematics.
- Completing a quest does not close the run; normal progression can continue
  where implemented. This feature does not implement MQ03's missing ending.

Each launch owns a fresh game, world, controllers, inventory and party. It copies
current settings into a non-persistent settings owner. Both journey and settings
stores have no disk path: the normal saved journey, Continue reference and
settings bytes are neither loaded nor changed. Restart, returning to the list,
and quitting release the private music and effects. Missing assets or an invalid
starting state return to the selector with an error, never to a fallback New Game.

`quest_playtest.py` owns metadata and explicit start builders;
`quest_playtest_ui.py` reuses catalogue browsing; `quest_playtest_session.py`
owns the disposable gameplay lifecycle. `Game._is_embedded` handles offscreen
display ownership, scaling and persistence isolation separately from
`Game._is_gallery_preview`, which alone restricts Gallery gameplay. Keep those
capabilities separate when extending either feature. Embedded input uses the
same viewport transform for events, live pointer polling and pause settings.

To register another implemented quest, add its start and metadata to the
playtest catalogue, prepare only its prerequisites using controller APIs, and
extend the catalogue/start tests. Do not list document-only quests or treat a
partially implemented quest as completed content.

Focused launcher verification:

```sh
PYTHONPATH=.:tests SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  python3 -m unittest test_quest_playtest test_quest_playtest_session test_title_screen
```

## Runtime boundaries

`quests.py` holds the state independently of rendering and NPC schedules.
`assets/quests/eldenmere.json` contains the opening quest's objectives. The state
flow is `available -> active -> ready -> completed`. Acceptance, objective
completion and reporting are guarded, idempotent operations. Halden comes first;
Elira and Venn then become eligible in either order. Reporting is a separate
operation from finishing the last household.

`social.py` selects Serene's offer, reminders, report and thanks from the saved
state. `speech_bubble.py` shares world-anchored bubble layout between drawing and
choice hit testing. Her work remains paused through the acceptance choice and resumes after
the opening's follow-up exchange. Refusal leaves her sorting provisions until
the request is accepted. The existing proximity release distance prevents immediate
retriggering. `quest_ui.py` projects interior quest givers onto exterior map
entrances without instantiating rooms or NPCs.
Quest notifications wait until the conversation ends, preserving their reading
time and keeping response buttons unobscured.

`opening.py` gates the offer, its marker and its journal listing until breakfast
has finished. The available-quest tracker instead gives local breakfast guidance
before then. The accepted click checkpoints the follow-up scene before the next
frame, so exiting immediately cannot skip that conversation on Continue. Walking
away from the live follow-up ends it and releases the actors while preserving
the accepted quest. Cancelling an offer or report uses a separate path from
finishing it, so unread pages never apply quest or conversation effects.

Future household controllers must call the following hook only after their
delivery, practical task and required scene have actually finished:

```python
from quests import OPENING_QUEST

game.quests.complete_objective(OPENING_QUEST, 'halden')
# Later, after their own completed tasks, in either order:
game.quests.complete_objective(OPENING_QUEST, 'elira')
game.quests.complete_objective(OPENING_QUEST, 'venn')
```

Halden's hook is now called by `halden_visit.py` only after medicine, three sacks,
the closing exchange, Tomas's goodbye and his actual departure through the door.
Room entry never calls these hooks.
There is no debug completion action in the player UI. Lifecycle, social and
gameplay tests exercise the ready/report and completion paths.
Elira's controller now delivers her food/oil, retrieves the lantern using the
stool, places it on her table and waits for the approved closing conversation
before completing her objective. Its local state and supply receipt persist
independently. Venn now delivers the recovery supplies, records both inspections,
offers two clicked repair choices and restores the gate/water before the closing
conversation completes the objective. Neither method affects major outcomes.
The later mill arrival/unlock
scene will be attached when MQ01's full story flow is implemented.

## Persistence

The launcher passes `saves/journey.json` to `Game`. `SaveStore` writes bounded,
versioned JSON through an atomic replacement; a failed write preserves the old
checkpoint. Save data records quest progress, conversation flags, player scene,
facing and position, the exterior map position, and the opening scene checkpoint. Quest snapshots are fully
validated before replacement; malformed state and unknown scene IDs cannot
partially load. A saved standing spot occupied by a restarted NPC falls back to
a clear entry/nearby landing.

New Game creates a fresh checkpoint; Continue restores an existing one. Accepted,
ready and completed state survive relaunch. Restoring never replays notifications
or resumes a partially read conversation. Ambient action clocks, prop reservations
and NPC positions are intentionally reconstructed from their existing routines.
Quest/conversation changes, door transfers and exit checkpoint automatically.
Direct test instances default to `save_path=None` and do not touch local saves.

## Verification

Run `SDL_AUDIODRIVER=dummy python -m unittest discover -s tests -q` for the
full suite. The focused quest tests cover lifecycle/order/idempotence, journal
rendering and scrolling, deliberate response hitboxes, routine resumption,
progress-sensitive dialogue, atomic save failures and title Continue behavior.

Shared-waypoint traffic now makes the lower-priority moving resident walk to a
nearby clear waiting point, let the other resident pass, and resume the same
authored task. The Serene full-cycle test exercises both ordinary timing and the
previously deadlocking random seed 2 with both actors present. Physical traffic
tests retain wall, NPC and player collision checks and unchanged task progress.
