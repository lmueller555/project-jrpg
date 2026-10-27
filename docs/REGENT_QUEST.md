# Aldric's visit and the regent quest

`CH01_MQ03` follows completion of Mira's mill quest. Caelan's job is to welcome and guide the visitors and help receive them at the sanctuary. Aldric settles a dispute concerning his road project; Caelan witnesses it and supplies only the mill status he knows firsthand.

## Playing through

Speak with Serene for the preparations exchange, then meet Aldric's party by the brook. Finish the greeting and accompany Aldric toward the road staging area. Read the disagreement between Mr. Venn and the foreman, Aldric's questions and settlement, and the clerk's confirmation of the hire terms. No receipt is a player target. Wait for the visible release of the cart and the crew's return to work, then continue to the courtyard.

Finish the welcome and meal before the excavation discussion. Aldric wants a preliminary survey within protected ground; Serene offers records and a joint review while withholding endorsement. Afterward, speak with Serene for Caelan's personal reaction and Tomas's call about the lanterns. That final exchange completes MQ03.

The visit preserves the revised role boundary: Caelan does not adjudicate a hire, direct a government account, negotiate the road project or decide excavation policy. The road foreman has a real logistical problem, and the cost of the delay is placed on the road account rather than the cart owner. The ruling takes effect in the world. The later disagreement remains unresolved.

## Dialogue and presentation

`assets/story/regent/scene.json` contains the six main scenes (`preparations`, `arrival`, `dispute`, `welcome`, `discussion`, `aftermath`) and short optional replies. Selected text carries brief parenthetical delivery cues for relief, anger, surprise, concern, laughter, hesitation and fatigue. These are intentionally occasional. Optional replies are stage-aware: the cart settlement and revised hire terms are discussed only after release, while Tomas refers to the meal only after the welcome. Earlier interactions use waiting replies.

The complete implementation script is [CH01_MQ03](narrative/game_01/CH01_MQ03.md). Ordinary dialogue stays live and cancelable. The visit gives the welcome, food, journey and personal reactions time before advancing its objectives. New officials use role titles instead of invented personal histories.

## Objectives and durable progress

The ordered objectives are `meet_visitors`, `accompany_visit`, `welcome_party` and `speak_serene`. The optional version-one `regent_quest` record stores a committed `stage` from:

`idle → assigned → met → dispute → releasing → escorting → welcome → hosted → discussion → done`.

The stage identifies the last completed dialogue/staging transition. Dialogue pages, action clocks and path caches are transient. Leaving unread preparations cannot accept the quest, and leaving an unread political conversation cannot endorse excavation. A completed settlement is checkpointed separately from the visible cart release. Old saves with MQ02 finished become eligible for the new visit; New Game resets it.

The same Mr. Venn actor participates, with his prior household progress intact. Serene and Tomas are staged for the visit without duplicating their actors. After MQ03, the controller keeps them at their courtyard festival-preparation stations until MQ04 takes ownership of Tomas for its school preparation session; their ordinary routines remain paused during that staging. The explicit Tomas handoff prevents this controller from moving or posing him after MQ04 borrows him; Serene retains her courtyard responsibilities. New Game releases this ownership and restores the ordinary sanctuary opening. The mill remains restored after MQ02.

## Chapter boundary

This quest does not issue formal excavation authorization. That remains the chapter-closing event after the Festival of Returning Light. Serene does not reveal the inherited warning, and no buried mechanism or ancient identity is established here. MQ04 now begins with Tomas’s lantern invitation, the school preparation session and Liam’s workshop outing.

## Design rule

For this quest and future quests, derive Caelan's participation from his relationships, responsibilities, knowledge and choices. Observation, support and witnessing a consequential decision can be sufficient. Add a player task only when there is a credible reason for Caelan to perform it.
