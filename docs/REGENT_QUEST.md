# Aldric's visit and the regent quest

This guide describes `regent_quest.py` and `assets/story/regent/scene.json`. The playable [MQ03 script](narrative/game_01/CH01_MQ03.md) implements the direct sanctuary visit, Lucan's introduction, Aldric's royal relationship and the ridge reserve's cultural and natural significance. The former Venn cart section is removed.

## Boundary after MQ02

MQ02 completes after Caelan returns from Halden, acknowledges Serene's destination instruction and physically places the clean cups. The [arrival cinematic](REGENT_ARRIVAL.md) follows, introducing Aldric's relief visit before returning control to Caelan's actual position in the sanctuary dining room. Speaking with Serene for her short welcome-visitors request separately accepts MQ03. The homecoming and bow question are not repeated.

## Playing through

1. Speak with Serene inside the dining room, then meet Aldric by the lower bridge.
2. Finish the greeting with Aldric, Lucan, the clerk and the driver. Lucan is Aldric's personal guard; he replaces the generic traveling attendant and remains a visitor rather than joining the combat party.
3. Guide the travelers directly through the courtyard entrance, sanctuary hall and dining-room door. There is no road-crew detour or intermediate dispute. The wagon remains at the village approach.
4. Wait for the visitors to reach their inside stations, then share the meal. Tomas asks about the wagon's brake; Caelan recalls his brother's breakfast promise to make sure everyone eats; Lucan watches the door.
5. Hear Aldric and Serene discuss the ridge survey after the meal. They consider the natural aether confluence, memorial grove and buried foundations, the public injury account and real material shortages. Serene offers courtyard stone, crew meals and cooperation with surface inspection and records. The trial excavation remains unresolved.
6. Let Aldric step aside toward the counter, then speak privately with Serene. Tomas's lantern invitation leads toward MQ04; the final acknowledgment completes MQ03.

The ordered objectives remain `meet_visitors`, `accompany_visit`, `welcome_party` and `speak_serene`. Caelan is a guide, host and witness. He gains no legal or survey authority and performs no receipt inspection. Venn's household and MQ01 progress are untouched; this controller no longer borrows him, stages a foreman or moves a cart.

## Dialogue and presentation

The runtime contains five main arrays: `preparations`, `arrival`, `welcome`, `discussion` and `aftermath`. Two greeting-only compatibility arrays, `arrival_unarmed` and `arrival_before_homecoming`, preserve older completed MQ02 journeys without inventing a sword gift or table-setting work. The canonical new-journey greeting remains unchanged. The [narrative script](narrative/game_01/CH01_MQ03.md) mirrors every main and optional exchange. Brief emotional and physical cues use literal asterisks. Dialogue remains player-paced and cancelable, with physical beats for the scabbard adjustment, bread, eating, guard attention, table clearing, survey, plan and account.

Aldric joins the household table and his companions gather at the right-hand tables. Four guest chairs provide seven seats in total. The middle aisle stays clear for the player and doorway. Lucan's attention is visible without making him negotiate in Aldric's place. Optional replies are stage-aware: the clerk mentions delivering copies only after the ridge discussion, while Tomas's earlier reply reflects the completed table-setting.

## Durable progress and old saves

The version-two `regent_quest` record stores the committed stage:

`idle → assigned → escorting → welcome → hosted → discussion → done`.

Partially read conversations, animation clocks, follow trails and path caches are never durable progress. The greeting records `meet_visitors`; Aldric's actual dining-room arrival records `accompany_visit`; the completed meal records `welcome_party`; the private exchange records `speak_serene` and completes the quest once.

Version-one `met`, `dispute`, `releasing` and `escorting` saves migrate to the direct escort. Other valid checkpoints retain their progress, including completed visits. Migration does not invent a cart release or start an excavation. Rebuilding the scene uses the same family and visitor actors, with no duplicate Lucan or caravan.

## Interior and later-quest ownership

Preparations, hospitality, the ridge discussion and the private aftermath use `sanctuary_dining`. Room-aware triggers cannot fire from matching coordinates outdoors. The same family members transfer from MQ02's homecoming after the arrival. After MQ03, Serene and Tomas stay at their dining-room stations until later quests explicitly borrow them. MQ03 stops moving or posing each actor after that handoff; New Game releases its ownership and restores the ordinary sanctuary opening.

## Story limits

The [regional surges](narrative/game_01/REGIONAL_SURGES.md), [planetary faith](world/ELDEN_VALE_FAITH.md) and [covenant](world/SANCTUARY_COVENANT.md) provide the scene's foundations. The natural confluence and grove explain why the whole reserve matters. They do not explain its buried works or prove what a shallow cut would do. The historic injury account is separate from the recent lightning incidents.

No formal excavation authorization is issued, and Serene's inherited warning remains undisclosed. The offered stone, meals, surface inspection and further records do not themselves repair the crossing or open a quarry. Lucan's recruitment remains later story work. MQ04 begins from Tomas's invitation about the lanterns.

## Design rule

Derive Caelan's participation from his relationships, responsibilities, knowledge and choices. Give him room to observe and react without making him settle a political or engineering decision beyond his role.
