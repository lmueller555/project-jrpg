# Aldric's visit and the regent quest

**Approval/runtime boundary (2026-10-31):** This guide describes the existing
`regent_quest.py` and `assets/story/regent/scene.json`, which still contain the
previous visit and excavation dialogue. The
[approved MQ03 revision](narrative/game_01/CH01_MQ03.md) now draws on the
[regional surges and relief work](narrative/game_01/REGIONAL_SURGES.md) and
[sanctuary covenant](world/SANCTUARY_COVENANT.md); those changes await runtime
integration. This documentation change does not add road damage, stone
handoffs or inspection activities to the playable quest.

MQ02 completion currently unlocks the visit, and the caravan appears through
the existing quest staging. The approved future handoff requires a caravan
arrival cutscene at the end of MQ02; that cutscene is not implemented.

`CH01_MQ03` follows completion of Mira's mill quest. Caelan's job is to welcome and guide the visitors and help receive them at the sanctuary. Aldric settles a dispute concerning his road project; Caelan witnesses it and supplies only the mill status he knows firsthand.

## Playing through

Find Serene preparing food at the sanctuary dining-room counter and Tomas arranging chairs for the preparations exchange, then meet Aldric's party by the brook. Finish the greeting and accompany Aldric toward the road staging area. Read the disagreement between Mr. Venn and the foreman, Aldric's questions and settlement, and the clerk's confirmation of the hire terms. No receipt is a player target. Wait for the visible release of the cart and the crew's return to work, then bring the party through the sanctuary hall to the dining room.

Finish the welcome and meal inside the dining room before the excavation discussion. Aldric joins the family table while his companions gather at the right-hand tables. Four spare chairs provide seven seats in total, and the middle aisle stays clear for Caelan and the doorway. Aldric steps aside toward the distant counter for Caelan’s final exchange with Serene. Aldric wants a preliminary survey within protected ground; Serene offers records and a joint review while withholding endorsement. Afterward, speak with Serene for Caelan's personal reaction and Tomas's call about the lanterns. That final exchange completes MQ03.

The visit preserves the revised role boundary: Caelan does not adjudicate a hire, direct a government account, negotiate the road project or decide excavation policy. The road foreman has a real logistical problem, and the cost of the delay is placed on the road account rather than the cart owner. The ruling takes effect in the world. The later disagreement remains unresolved.

## Dialogue and presentation

`assets/story/regent/scene.json` contains the six main scenes (`preparations`, `arrival`, `dispute`, `welcome`, `discussion`, `aftermath`) and short optional replies. Selected text carries brief parenthetical delivery cues for relief, anger, surprise, concern, laughter, hesitation and fatigue. These are intentionally occasional. Optional replies are stage-aware: the cart settlement and revised hire terms are discussed only after release, while Tomas refers to the meal only after the welcome. Earlier interactions use waiting replies.

The [approved narrative target](narrative/game_01/CH01_MQ03.md) includes the new lightning damage, relief-driven quarry request and concrete covenant discussion; the current runtime dialogue has not yet adopted them. Ordinary dialogue stays live and cancelable. The existing visit gives the welcome, food, journey and personal reactions time before advancing its objectives. New officials use role titles instead of invented personal histories.

## Objectives and durable progress

The ordered objectives are `meet_visitors`, `accompany_visit`, `welcome_party` and `speak_serene`. The optional version-one `regent_quest` record stores a committed `stage` from:

`idle → assigned → met → dispute → releasing → escorting → welcome → hosted → discussion → done`.

The stage identifies the last completed dialogue/staging transition. Dialogue pages, action clocks and path caches are transient. Leaving unread preparations cannot accept the quest, and leaving an unread political conversation cannot endorse excavation. A completed settlement is checkpointed separately from the visible cart release. Old saves with MQ02 finished become eligible for the new visit; New Game resets it.

The same Mr. Venn actor participates, with his prior household progress intact. Serene and Tomas are staged for the visit without duplicating their actors. After MQ03, the controller keeps them at their dining-room stations until MQ04 takes ownership of Tomas for its school preparation session; their ordinary routines remain paused during that staging. The explicit Tomas handoff prevents this controller from moving or posing him after MQ04 borrows him; Serene retains the dining-room preparations until a later scene explicitly borrows her. New Game releases this ownership and restores the ordinary sanctuary opening. The mill remains restored after MQ02.

## Chapter boundary

This quest does not issue formal excavation authorization. That remains the chapter-closing event after the Festival of Light. Serene does not reveal the inherited warning, and no buried mechanism or ancient identity is established here. MQ04 now begins with Tomas’s lantern invitation, the school preparation session and Liam’s workshop outing.

## Design rule

For this quest and future quests, derive Caelan's participation from his relationships, responsibilities, knowledge and choices. Observation, support and witnessing a consequential decision can be sufficient. Add a player task only when there is a credible reason for Caelan to perform it.

## Interior staging and saved journeys

Preparations, hospitality, the political discussion and the personal aftermath all use `sanctuary_dining`. Room-aware triggers cannot fire from matching coordinates outdoors. Guests follow Caelan through the existing courtyard entrance, sanctuary hall and dining-room door; the escort objective completes only after Aldric reaches the dining room. The former `courtyard` station key remains a data compatibility alias for the dining-room welcome. Four quest-owned chairs reference existing furniture art and provide seven chairs in total without changing the earlier breakfast map. Their feet block movement while the central doorway route remains clear.

Version-one quest stages remain valid. Loading any committed hospitality checkpoint places the same actors inside the dining room, including journeys saved at the old outdoor stations. Preparing and speaking inside use the same cancel-safe dialogue commits. Later quests borrow the actual Serene and Tomas actors explicitly, and MQ03 stops moving or posing each actor after that handoff.
