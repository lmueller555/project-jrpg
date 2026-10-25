# Quest feedback and progress

The quest layer provides availability, explicit acceptance, objective updates,
ready-to-report state and completion. The opening assignment is available from
Mother Serene; its household task implementations remain future work. The
approved story order remains in `narrative/game_01/CH01_MQ01.md`.

## Player controls

- Approach Serene while facing her to speak. Her gold `!` appears overhead and
  at the sanctuary entrance on the town map, including when she moves rooms.
- Advance prose by clicking anywhere, Space or E. At the response prompt only
  clicking **I'll help** accepts; **Not just yet** leaves the quest available.
- Use **J** for the journal. J or Escape closes it; wheel, arrows and Page Up/Down
  scroll. Movement, dialogue triggers and room entry are suspended while open.
- The tracker follows the next eligible objective. Completed objectives gain
  checkmarks, queued ones stay distinct, and `?` replaces `!` when reporting is
  available. Reading Serene's final report page completes a ready quest.
- Acceptance and completion banners include the quest title; objective notices
  name the work finished. Chimes obey the title screen's music setting and
  missing audio hardware does not prevent play.

## Runtime boundaries

`quests.py` holds the state independently of rendering and NPC schedules.
`assets/quests/eldenmere.json` contains the opening quest's objectives. The state
flow is `available -> active -> ready -> completed`. Acceptance, objective
completion and reporting are guarded, idempotent operations. Halden comes first;
Elira and Venn then become eligible in either order. Reporting is a separate
operation from finishing the last household.

`social.py` selects Serene's offer, reminders, report and thanks from the saved
state. Her work remains paused through the acceptance choice and resumes after
acceptance or refusal. The existing proximity release distance prevents immediate
retriggering. `quest_ui.py` projects interior quest givers onto exterior map
entrances without instantiating rooms or NPCs.

Future household controllers must call the following hook only after their
delivery, practical task and required scene have actually finished:

```python
from quests import OPENING_QUEST

game.quests.complete_objective(OPENING_QUEST, 'halden')
# Later, after their own completed tasks, in either order:
game.quests.complete_objective(OPENING_QUEST, 'elira')
game.quests.complete_objective(OPENING_QUEST, 'venn')
```

Halden's hook includes Tomas's departure. Room entry never calls these hooks.
There is no debug completion action in the player UI. The ready/report and
completion paths are exercised by lifecycle, social and gameplay tests while
the actual task controllers are still pending. The later mill arrival/unlock
scene will be attached when MQ01's full story flow is implemented.

## Persistence

The launcher passes `saves/journey.json` to `Game`. `SaveStore` writes bounded,
versioned JSON through an atomic replacement; a failed write preserves the old
checkpoint. Save data records quest progress, conversation flags, player scene,
facing and position, and the exterior map position. Quest snapshots are fully
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

The existing Serene full-cycle test fixes Tomas's random wait timing locally so
it measures a repeatable schedule with both actors present. Independent of the
quest system, some wait timings can leave Serene and Tomas waiting for the same
narrow dining-room doorway waypoint (reproduced with random seed 2). That shared
route scheduling issue remains separate; quest input and room-visit tests do
not bypass collision or complete tasks to work around it.
