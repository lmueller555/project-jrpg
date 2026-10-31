# Project JRPG

Explore Eldenmere and the surrounding Elden Vale as Caelan by running `main.py`. The game uses 24×24 terrain and 24×36 character art, with live movement, collision, a following camera and animated scenery. The retained story and asset tooling are documented below.

## Music files

Add your music files to [`assets/music/`](assets/music/). The folder's README
covers formats, filenames and optional track notes.

## Test combat

A repeatable Bat hovers on the grass west of Eldenmere's well. Walk or run into
it to start a test battle, even before the mill quest. After returning, step
away and approach again; the normal four-second respawn cooldown applies.
See the [combat guide](docs/COMBAT.md) for its location and battle controls.

## Play Eldenmere

Use Python 3.10 or newer. From the repository folder:

```sh
python -m pip install -r requirements.txt
python main.py
```

In VS Code, select the Python interpreter where you installed the dependency, open `main.py` and choose **Run Python File**, or use the **Play Eldenmere** launch configuration with F5. No asset-building step is required. Paths are resolved relative to `main.py`, so launching from another working directory also works.

The game launches fullscreen at the desktop display size. Press **F11** to
switch to a resizable 960×640 window and back; your window size is remembered
for that session. Use `python main.py --windowed` to launch directly in a window.
Headless verification stays windowed for consistent screenshots. The internal
480×320 world canvas keeps crisp integer scaling and centered borders where
needed to preserve the pixel art's proportions. Interface text is rendered
separately at display resolution with the bundled Atkinson Hyperlegible fonts,
so letters have smooth, readable edges instead of enlarged bitmap shapes.

The game now opens on an animated Eldenmere title screen with a **bottom-center
menu**. Click New Game, or use arrows and Enter, to begin with a somber cinematic
glimpse of Caelan and Mira later in their journey. Layered sanctuary and valley
art, quiet character animation and camera shots lead into Caelan's opening
morning. **Esc** pauses/resumes the cinematic and its music; a small **Skip**
button remains available in the bottom-right corner. Continue resumes the saved
journey directly. See the [opening cinematic guide](docs/OPENING_CINEMATIC.md).
Settings changes fullscreen/windowed mode, independent music/effects levels,
text size, reduced interface motion and objective visibility. Continue resumes
a saved journey when one exists. The logo uses **The Broken Covenant** as a working title.
See the [title screen preview](docs/reviews/title_screen/README.md) for review.
The current green-and-brass menus, parchment ledger/map and text-rendering
rules are documented in [UI design](docs/UI_DESIGN.md).

Tomas now helps with preparations and tinkers in the sanctuary dining room,
then takes a courtyard break. He uses the portrait dialogue system and safely
sets down carried work before speaking. See his [routine previews](docs/reviews/tomas_routines/README.md).

The title water animates throughout the brook, pools, mill discharge and
foreground cascades. Your **Eldenmere Theme** now loops on the title screen and
through Eldenmere, its interiors and the millrace, continuing across Continue
and area transfers. **Dare to Dream Leitmotif** loops throughout the New Game
cinematic, then hands back to Eldenmere Theme when it ends or is skipped.
**Kindled Courage** plays in battles. MQ02 now
stages a cutscene on millrace arrival: Caelan and Mira stop, the camera pans to
the boar for their conversation, then returns on Mira's “come back to me” warning.
The score and fight begin only after the camera is back and the warning is read,
continuing through the world-to-battle curtain and reveal. Reduced
Motion uses a short plain fade. Victories play **Triumphal Fanfare** once and
show a victory banner before opening **Spoils of Battle**, where RP and items
are awarded. After the fanfare ends, Spoils stays silent until Continue returns
to the world theme. Victory checkpoints survive quitting without losing or
duplicating rewards. The Music slider controls the soundtrack independently of effects. See the [music assets](assets/music/README.md) and
[music/transition preview](docs/reviews/battle_music_transition/README.md) and
[victory/Spoils review](docs/reviews/victory_spoils/README.md).

| Control | Action |
| --- | --- |
| WASD or arrow keys | Move Caelan |
| Shift | Run with Caelan’s approved four-direction running animations |
| M | Open/close the town or regional map; click landmarks to inspect them |
| Click the overworld minimap | Open the illustrated regional atlas |
| J | Open/close the quest journal; select a quest and scroll its details |
| I | Open/close the inventory; Tab or left/right switches categories |
| Left click anywhere / Space / E | Advance an open conversation |
| E near a bedroom furnishing | Inspect it when the prompt appears |
| Click a response button | Accept a quest or leave it for later |
| F11 | Toggle fullscreen |
| Escape | Close the journal/map, or pause/resume |

The resizable window uses crisp integer pixel scaling. Explore the full approved 64×56-tile layout, both brook bridges, the sanctuary and eastern terrace stairs, all six cottages, the watermill, workshop and commons. Buildings, water, terrace walls and solid props block movement; roofs, trees and bridge rails draw at the appropriate depth. Water, the mill wheel, chimney smoke, lanterns and existing vegetation animate.

The commons now contains a roofed stone well, a rounded dirt-and-stone square and a southern path connection. The well has solid collision, roof occlusion and subtle water glints; the map labels this area **Well square**. The [updated town layout and in-game previews](docs/reviews/eldenmere_well/README.md) are approved by the user.

**Building doors open automatically when you approach.** They stay open nearby and close as you move away. Walk into an open doorway to enter; walk down through the interior's entrance threshold to return outside. No action key is required. The sanctuary hall also connects to Caelan's bedroom and the dining room through its northern doors.

All nine buildings have separate furnished interiors. Cottages use the approved 10×10, 13×10 and 16×10 layouts; the sanctuary uses its three approved rooms. The workshop and mill workrooms reuse the approved furniture and interior kit. Rooms include furniture collision, ambient lighting and hearth/steam animation where present. Smaller rooms are centered in the viewport, and M still shows the town map while indoors.

The southern road now leads automatically to the [Elden Vale overworld](docs/OVERWORLD.md), a streamed regional landscape between two rivers, with northern woodland, eastern foothills, southern fields, guarded stone walls and the lightning-destroyed western bridge. Approach the miniature of Eldenmere to return through the village's southern entrance. Press M for the regional map, with zoom, drag and landmark details. The checkpoints and ruined bridge keep onward exploration closed until future opening-story work explicitly opens it. See the [actual-game region previews](docs/reviews/elden_vale_overworld/README.md).

The [environment quality pass](docs/reviews/elden_vale_polish/README.md) gives the vale distinct farmsteads and crop parcels, orchards, clustered forests, rocky slopes and planted riverbanks. Worn stone roads, cart tracks and woodland paths connect the new scenery, with wildlife, laundry, relief supplies and small resting places adding local character.

The [place-composition pass](docs/reviews/elden_vale_composition/README.md) brings farm working areas, property boundaries, orchard arrivals, relief loading and gate duty stations into connected arrangements. The destroyed western bridge now has a three-tile-wide roadway, with a collapsed center that keeps the crossing closed.

The [region NPC animation pass](docs/REGION_NPCS.md) adds authored full-body
working and directional carrying poses for the grain workers, with registered
hand grips and supported loads. Checkpoint guards have directional conversation
poses and a portrait matching their silver armor, closed helmet and navy tabard.

The [illustrated regional atlas](docs/REGIONAL_MAP.md) adds detailed cartography, live place labels and passage states, a compact selection card, and a north-up overworld minimap. Click the minimap or press M to open the atlas. The exploration Menu button has been removed throughout the game; Escape still pauses. See the [atlas and minimap previews](docs/reviews/elden_vale_atlas/README.md).

Mother Serene now follows one continuous sanctuary schedule. She sorts the household provisions, checks the preparation list, tends the dining-room hearth and walks through the real connecting doorway to arrange linens in the hall. Her position and action clock persist when Caelan changes rooms; she yields when he blocks a route or doorway landing. The four [enlarged in-room routine previews](docs/reviews/serene_sanctuary_routines/README.md) await user review.

Mira now works at the bench outside her shop: she inspects a fitting, makes three wrench strokes, tests it by hand and rests. Her [enlarged looping preview](docs/reviews/mira_bench/bench_closeup.gif) is approved by the user. She has foot collision and draws at the appropriate depth; the shop entrance remains clear.

The auburn-haired gardener in the sage dress draws water from the commons well using her own pail. At the near side, she turns away and raises the pail behind her torso while only a three-pixel iron hook hangs beneath the windlass. The concealed pail then snaps to a fully visible parked position directly beneath the spindle and settles by one pixel. It descends with the rope, disappears progressively behind the front rim, fills, and returns visibly to the same top position. During retrieval it snaps behind her torso before emerging at her side. She waters four flower patches and both window troughs, then rests for a randomly chosen 3–5 minutes. She yields to Caelan, takes safe detours where possible and keeps her work/rest and well progress while you visit interiors. The [new enlarged loop and full routine](docs/reviews/gardener_top_winch_bucket/README.md) are approved; earlier versions remain historical review records. Other villagers and quests remain future work.

**Dialogue happens in the running world.** Walk close while
facing Mother Serene in the sanctuary hall or dining room. She safely sets down her work,
turns and pauses. A compact speech bubble above the current speaker contains
their approved portrait; Caelan's replies follow him. Click anywhere in the
window, Space or E to advance. Caelan can keep moving, the camera keeps following
him, and other NPC routines and scenery continue. Walking away or changing rooms
closes unfinished dialogue without setting conversation flags, accepting a quest
or completing a report. Step away before approaching again after a completed
conversation. Completed conversation flags and quest progress are saved.
See the [earlier dialogue preview](docs/reviews/proximity_dialogue/README.md).
Mira’s main-scenario conversations are playable in MQ02; gardener conversations remain future work.

**Mira’s mill quest is playable after MQ01.** Meet her at the outdoor workbench,
inspect the stopped mill beside its wheel and channel, then follow the north road
to the map boundary and use **E** to reach the upper millrace.
Help her unload the intake, move a small pocket of still water with magicks,
and finish their encouragement exchange. Free the intake together with the
lever and haul rope, return to the visibly running mill, and speak with Halden.
The same Mira actor follows through doors and trail links; progress survives
leaving and reloading. See the [quest guide](docs/MILL_QUEST.md) and
[in-game previews](docs/reviews/mill_quest/README.md).

**Aldric arrives after the mill quest.** A detailed, player-advanced
[cinematic](docs/REGENT_ARRIVAL.md) shows his caravan admitted at the southern
land gate, his conversation with locals about the ruined crossing, and Serene's
private reaction from inside the sanctuary. Escape pauses/resumes; Skip ends
the scene without accepting MQ03 or changing Caelan's location.

**The Regent’s Road is playable after the mill quest.** Meet Serene and Tomas
in the sanctuary dining room, greet Aldric’s visitors by the brook, and guide them
through the village. Aldric and his clerk handle the road crew’s cart dispute;
Caelan contributes only what he knows about the working mill. The released cart
leaves with Mr. Venn, and the party continues to the sanctuary for a welcome,
a measured excavation discussion and a private exchange with Serene. Dialogue
includes occasional emotional cues and remains live and cancelable. The visit
does not authorize excavation or start the festival quest. See the
[quest guide](docs/REGENT_QUEST.md) and [arrival review](docs/reviews/regent_arrival/README.md).

**Quest feedback is available in-game.** Mother Serene has an outlined gold `!`
in the sanctuary and on the town map. Approach her to hear the opening request;
after advancing the dialogue, click **I'll help** or **Not just yet**. Clicking
elsewhere or pressing the dialogue-advance keys cannot choose for you. Accepted
quests show a titled banner, a short chime, a current-objective tracker and a
scrollable **J** ledger with separate quest selection and details. Objective
updates, a `?` ready-to-report marker, and
completion feedback share the same quest state. Effects settings control quest
chimes independently of music. The journal pauses player movement and doorway entry.

**The sanctuary opening is playable from New Game.** Caelan wakes to Tomas's
knock in his bedroom. After their exchange, explore freely and use E to inspect
nearby furnishings, then walk through the hall to breakfast in the northeast
room. The family greets him at the entrance, then he walks to his chair, sits,
eats a small bite and sets out Serene's cup before standing. Tomas nudges his
plate and eats while Serene sorts supplies. Furniture and collision stay fixed.
After breakfast, approach Serene for her request and click an explicit response.
Acceptance continues into the approved exchange about Tomas helping and Caelan
eating enough, then leaves the quest tracked in the journal. The morning includes
quiet bells, knocks, birds and stream ambience, plus synchronized cloth, chair,
footstep, plate and cup sounds controlled by the effects level.

The camera keeps the full world viewport throughout dialogue and actions.
MQ02’s millrace introduction briefly owns movement and the camera for its staged
boar/party shots; ordinary conversations remain live. See the
[millrace cutscene preview](docs/reviews/millrace_cutscene/README.md).
Portrait bubbles stay within the screen and their response buttons move with
them. The breakfast invitation, inspections and accepted-quest conversation
allow free movement. Walking away from the invitation leaves breakfast available
through **E: join breakfast** near the table or a later dining-room visit.
Getting out of bed and the guided sitting/meal/standing actions still control
Caelan's body; four-pose actions finish even when prose is advanced quickly.
Pressing a movement key while seated finishes the gestures and stands him up,
so unread dialogue never holds him at the table.
**Escape** opens a modal pause menu during exploration, dialogue or actions.
Characters, Aether Lattice, Inventory, Journal, Map and Settings are available there alongside Resume and Quit; the
controls reference is inside Settings. Pausing holds NPC, action, camera and
ambience clocks. Music and effects have separate sliders with percentage displays,
mouse adjustment and
left/right or +/- keys. Settings also provides 100%, 125% or 150% text, reduced
interface motion and objective-tracker visibility. Preferences persist in
`saves/settings.json` independently of the journey.

Exploration uses a brief location plaque and nearby interaction prompts instead
of a permanent controls strip. Dialogue choices show hover/pressed feedback,
and menus use the same lantern selection mark, spacing and panel treatment.

Caelan's bed in the Sanctuary bedroom is a free rest point. Approach its side
or foot, press **E**, then choose **Rest** to fully recover the party's HP and
MP. A brief fade marks the rest, and the recovered resources are saved.

Continue preserves the opening checkpoint without replaying finished scenes.
Saves from before this opening was added keep their existing location/progress;
choose **New Game** to experience the new beginning. See [story implementation](docs/STORY_IMPLEMENTATION.md).

The opening dialogue introduces the household names, their work and needs,
and the bridges or terrace that lead to them. Festival of Light preparations
connect the deliveries, Halden’s flour and Mira’s repair work. Spoken reminders
repeat the destinations, and brief emotional cues appear as literal `*emotes*`.

Tomas now joins Caelan after acceptance and follows through town and doors.
Approach Halden in his cottage to deliver the medicine, then use **E** to move
three sacks from the entry to the dry pallet; Tomas carries the middle sack.
After Halden's closing conversation and Tomas's goodbye, Tomas walks out and
returns to his preparations. Elira and Venn unlock in either order. Elira's visit
is playable: deliver her supplies, use **E** at the stool to retrieve her memorial
lantern, set it on her table with **E**, then speak with her. At the Venn cottage,
deliver the recovery supplies to either parent. Use **E** to inspect the gate pin
and blocked channel east of their house, then click a repair choice. Borrowed
tools restore the flow. A magick attempt produces a trace of energy but fails
to move the current; Caelan then completes the repair with tools. Return to the
family to finish the visit. Visiting a house never completes a task.
See [Halden](docs/HALDEN_VISIT.md), [Elira](docs/ELIRA_VISIT.md) and [Venn](docs/VENN_VISIT.md).

After all three visits, report to Serene. She returns to the sanctuary hall,
where Halden arrives through the courtyard door with news that the mill wheel
has stopped. Finish their exchange to complete the errand and reveal
**A Little Trouble at the Mill**, with an objective pointing to Mira's workshop.
The mill quest continues from that handoff. Older saves that already turned
in the errands receive the missing arrival without repeating the household work.
See the [conclusion preview](docs/reviews/opening_conclusion/README.md).

**Caelan's satchel is available with I or Pause → Inventory.** Weapons, Armor,
Items and Key Items have separate categories, quantity counts and readable item
details. Accepting Serene's request grants the three household supply bundles
once, including Halden's medicine. Key Items are protected from ordinary removal;
successful quest handoffs consume them and save a delivery receipt. The delivery
API handles all three households' supplies; entering a house never consumes
them. Older journeys receive only outstanding supplies, and New Game starts
with an empty satchel. See [inventory design and integration](docs/INVENTORY.md).

**Caelan's attributes are available through Pause → Characters.** He begins as a
balanced all-rounder with 140 HP, 30 MP and 10 each in Str, Mag, Spr, Def,
M. Def, Speed, Acc, Eva and Lck. Mag powers damaging spells; Spr powers healing
spells. Each attribute has its own icon; hover an icon or stat card to read its
tooltip, or use the keyboard to select an attribute and read its description.
Current HP/MP and all attributes persist with the journey. Older saves without
attributes receive the starting profile; the original 300-HP profile migrates
to 140 HP while preserving its health proportion. New Game resets the profile. See
[attribute definitions and starting values](docs/CHARACTER_ATTRIBUTES.md).
Characters also shows Attunement and RP progress. The approved
[per-hit damage formula](docs/DAMAGE_FORMULA.md) is implemented in
`combat_damage.py`, with physical/magical attribute pairs and 9,999/99,999
damage limits. The first [wait-ATB battle](docs/COMBAT.md) is playable against
a visible Bat on the grass west of the well. Approach and press **E** when
**Engage Bat** appears. The separate battle scene includes Caelan's combat
animations, Attack, Guard, Flee and learned Aether Dart, plus the bottom HP/MP/ATB
panel. All gauges pause while the player chooses; enemy ATB is hidden. See the
[combat preview](docs/reviews/atb_combat/README.md).

**Pause → Aether Lattice** opens the connected progression board. Battle-earned
Resonance Points increase Attunement Rank; each gained rank awards one Lattice
Step. Every connection crossed costs one Step, including blank nodes and
backtracking. Reaching a stat or ability node makes it available for activation
with the matching Aether Crystal. Movement and activation are separate actions;
unactivated nodes remain traversable. The 200-node section includes large and
small circular formations, rank gates, all eleven attributes and twenty ability nodes.
Node bonuses persist without being applied again on Continue. HP/MP nodes raise
capacity without refilling current resources. See the
[Aether Lattice reference](docs/AETHER_LATTICE.md).

Bat victories use the battle-reward interface. Normal journeys begin
at Attunement 1 with zero RP, zero Steps and no crystals; opening quests do not
grant sample rewards. Review the system immediately in an isolated temporary
journey with `python tools/preview_aether_lattice.py`, or use
`--rp 500 --crystals 10` for a richer preview. The ordinary player save and
settings are kept separate from that preview.

The launcher automatically checkpoints quest/conversation changes, room transfers,
and exit to `saves/journey.json` beside `main.py`; the local saves folder is ignored
by Git. **Continue** restores quest facts, dialogue history, attributes, lattice progress and player location
without replaying old notifications. Ambient NPC routines restart on launch;
their moment-to-moment action clocks are not part of this save. **New Game** starts
a fresh journey and replaces that checkpoint. A missing or unreadable save leaves
Continue unavailable. Tests construct `Game(save_path=None)` to stay in memory.

Verify the runtime without a display:

```sh
python -m unittest discover -s tests -v
python main.py --headless --frames 120 --screenshot screenshots/eldenmere.png
```

The runtime requires only Pygame. The checked-in [playable map](assets/maps/eldenmere/playable/README.md) is compiled from approved art; rebuilding it is an optional development step requiring the separate Pillow asset environment.

See the [gameplay capture](docs/reviews/playable_eldenmere/gameplay.gif) and [in-game town map](docs/reviews/playable_eldenmere/town_map.png) for a preview from the running game.

The [door and interior preview](docs/reviews/building_doors/doors_and_interior.gif) demonstrates automatic opening/closing and a sanctuary entry/exit in the running game.

## Story documents

- [Foundational lore](docs/FOUNDATIONAL_LORE.md): cosmology, ancient history, and established worldbuilding.
- [Auratia world atlas](docs/world/WORLD_ATLAS.md): approved continental geography, regional cultures, and Eldenmere's wider setting.
- [Classroom world map](docs/WORLD_MAP.md): inspect Auratia’s map at the village school, including its northern and southern polar regions.
- [Saga bible](docs/narrative/saga/SAGA_BIBLE.md): overarching narrative and multi-game boundaries.
- [Revelation plan](docs/narrative/saga/REVELATION_PLAN.md): player knowledge and disclosure constraints.
- [Game I story bible](docs/narrative/game_01/STORY_BIBLE.md): game-level requirements and an earlier alternative premise.
- [Game I act outline](docs/narrative/game_01/ACT_OUTLINE.md): the proposed direction, *The Broken Covenant*.
- [Approved companion foundations](docs/narrative/game_01/COMPANIONS.md): Lucan, Rhea and Edran’s backgrounds, personalities, combat roles and introduction windows.
- [Chapter 1: Life in Eldenmere](docs/narrative/game_01/CHAPTER_01.md): approved opening structure.
- [Regional surges and Aldric's relief visit](docs/narrative/game_01/REGIONAL_SURGES.md): southern-road damage, repair pressures and the end-MQ02 caravan arrival.
- [Sanctuary covenant](docs/world/SANCTUARY_COVENANT.md): approved protected-ground boundaries, custodial duties, public evidence and the unresolved trial-cut request.
- [Opening quest: A Day Like Any Other](docs/narrative/game_01/CH01_MQ01.md): approved first-quest narrative and dialogue.

Status labels distinguish approved story decisions, proposals and open questions.
The approved local revisions above update the opening's canon without approving
the entire working act outline. Runtime guides identify the remaining gameplay work.

## New character art

[Lucan, Rhea and Edran's base sprites](docs/reviews/companion_sprites/README.md)
are approved in front overworld, combat-ready and cinematic standing formats.
Rhea has a green dress, blonde hair, blue eyes and a purple tanglewood staff
with a green orb; Edran uses his revised sky-blue and silver outfit.
Their [front walking cycles](docs/reviews/companion_front_walks/README.md)
are approved, with animated comparisons and a town-renderer movement preview.
Their [four-direction idle sets](docs/reviews/companion_directional_idles/README.md)
are also approved, with side and rear views retaining each character's equipment placement.
Their [complete walking sets](docs/reviews/companion_directional_walks/README.md)
are approved in all four directions, with animated comparisons and town movement previews.

[Caelan's idle sprites](assets/characters/caelan/README.md) begin the new art library at 24×36 pixels per frame. All four directional idle designs are approved.

The approved [front-facing walk cycle](assets/characters/caelan/walk_front/README.md) contains four frames with coordinated head-and-shoulder bobbing and an enlarged looping GIF.

Matching [left](assets/characters/caelan/walk_left/README.md), [right](assets/characters/caelan/walk_right/README.md), and [back](assets/characters/caelan/walk_back/README.md) walking cycles are approved. The [combined looping preview](assets/characters/caelan/walk_directions_review.gif) shows all four approved directions together.

[Mira's design](assets/characters/mira/README.md) is approved: dark brown ponytail, cream flower, pink working shirt, charcoal trousers, boots, and tool pouch. Her front idle sprite is available for review at the same 24×36 scale, with shared pose components and editable assembly layers.

Her [front walking animation](assets/characters/mira/walk_front/README.md) is approved. It is assembled from character-specific parts and the shared Caelan pose template using the [repeatable asset builder](tools/README.md).

Her [left](assets/characters/mira/walk_left/README.md), [right](assets/characters/mira/walk_right/README.md) and [back](assets/characters/mira/walk_back/README.md) walks and new facing appearances are approved. The [combined looping preview](assets/characters/mira/walk_directions_review.gif) shows all four directions together.

The first [generic male NPC](assets/characters/npcs/male_01/README.md) front idle is approved: brown hair, a moss-green shirt, tan trousers and brown boots. Both additional palette variants are approved: [black hair, rust shirt and charcoal trousers](assets/characters/npcs/male_02/README.md), and [gray hair, slate shirt and brown trousers](assets/characters/npcs/male_03/README.md). The [enlarged comparison](assets/characters/npcs/male_variants_review.png) shows all three. These start the planned set of two NPC base designs with three palette variants each.

All three male NPC palettes have approved front, left, right and back stationary idles at 24×36. The [directional comparison](assets/characters/npcs/male_idle_directions_review.png) shows variants as rows and front, left, right, back as columns. All twelve directional idle frames are approved. All three palettes also have approved walking cycles in all four directions.

The base male NPC's [four-frame front walk](assets/characters/npcs/male_01/walk_front/README.md) is approved. It uses the shared stride, tan-trouser/brown-boot colors and coordinated head-and-shoulder bob. The [enlarged looping preview](assets/characters/npcs/male_01/walk_front/walk_front_preview.gif) plays all four frames at 140 ms each.

The [rust/charcoal](assets/characters/npcs/male_02/walk_front/README.md) and [slate/brown](assets/characters/npcs/male_03/walk_front/README.md) front-walk variants are approved. The [synchronized comparison](assets/characters/npcs/male_walk_front_variants_review.gif) shows all three palettes using the same stride, timing and bob.

The base male NPC's [left](assets/characters/npcs/male_01/walk_left/README.md), [right](assets/characters/npcs/male_01/walk_right/README.md) and [back](assets/characters/npcs/male_01/walk_back/README.md) walking cycles are approved. The [four-direction looping preview](assets/characters/npcs/male_01/walk_directions_review.gif) includes the approved front walk for comparison. The other palette walks use these approved base cycles.

The rust/charcoal and slate/brown left, right and back walks are approved. The [complete synchronized grid](assets/characters/npcs/male_walk_all_variants_review.gif) shows directions as rows and palettes as columns. Enlarged comparisons are also available for [left](assets/characters/npcs/male_walk_left_variants_review.gif), [right](assets/characters/npcs/male_walk_right_variants_review.gif) and [back](assets/characters/npcs/male_walk_back_variants_review.gif). All twelve male NPC walking cycles are approved.

The female NPC left/right profile-jaw cleanup is approved by the user. [Before/after comparisons](docs/reviews/female_profile_chin/README.md) show the three-pixel skin-shading correction across all palettes and the gardener; approved stride and body motion are preserved.

The first [female NPC front idle](assets/characters/npcs/female_01/README.md) is approved: dark hair in a low bun, a blue calf-length dress with short sleeves and brown ankle boots, at the same 24×36 scale. The [enlarged preview](assets/characters/npcs/female_01/idle_front_review.png) and [scale comparison](assets/characters/npcs/female_01/scale_comparison.png) show the approved design. All four directional idles and all four blue base walking cycles are approved.

All three female front-idle palettes are approved: dark hair/blue dress/blue eyes, auburn hair/sage dress/green eyes and blonde hair/plum dress/hazel eyes. The [enlarged comparison](assets/characters/npcs/female_variants_review.png) shows the same silhouette across all three; [eye close-ups](assets/characters/npcs/female_eyes_review.png) show the pupil and iris differences.

The [female directional review](assets/characters/npcs/female_idle_directions_review.png) shows all three palettes as rows and front, left, right, back as columns. All twelve directional idles are approved, with a visible low bun, the shared row-28 dress hem and exposed ankle boots. Profiles have one blue, green or hazel iris accent; back views show no eyes. [Profile close-ups](assets/characters/npcs/female_profile_eyes_review.png) compare those iris colors.

The blue base female NPC has an approved [four-frame front walk](assets/characters/npcs/female_01/walk_front/README.md), using the shared stride and coordinated bob with dedicated dress poses. The [20× looping preview](assets/characters/npcs/female_01/walk_front/walk_front_preview.gif) shows the one-pixel skirt sway, passing hem lift and visible ankle boots. This cycle is approved; palette variants and other walking directions will use its timing and dress motion.

The blue female NPC has approved [left](assets/characters/npcs/female_01/walk_left/README.md), [right](assets/characters/npcs/female_01/walk_right/README.md) and [back](assets/characters/npcs/female_01/walk_back/README.md) walks. The [four-direction looping preview](assets/characters/npcs/female_01/walk_directions_review.gif) includes the approved front cycle for comparison. All four cycles are approved and preserve the bun, profile eye, coordinated bob, dress hem motion and visible ankle boots.

The [sage/green-eye](assets/characters/npcs/female_02/README.md) and [plum/hazel-eye](assets/characters/npcs/female_03/README.md) walking palettes are approved in all four directions. They preserve every approved blue-base pose and timing. The [complete synchronized grid](assets/characters/npcs/female_walk_all_variants_review.gif) shows front, left, right and back as rows; blue, sage and plum as columns. Larger three-palette comparisons are available for [front](assets/characters/npcs/female_walk_front_variants_review.gif), [left](assets/characters/npcs/female_walk_left_variants_review.gif), [right](assets/characters/npcs/female_walk_right_variants_review.gif) and [back](assets/characters/npcs/female_walk_back_variants_review.gif).

## New terrain art

The first [Eldenmere grass/dirt pack](assets/terrain/eldenmere/grass_dirt/README.md) is approved at 24×24 pixels per tile. It contains four grass variations, a transparent 47-tile dirt blob atlas and three dirt interiors. The [character-scale review](assets/terrain/eldenmere/grass_dirt/review_scene.png), [complete blob atlas](assets/terrain/eldenmere/grass_dirt/blob_47_review.png) and [material samples](assets/terrain/eldenmere/grass_dirt/materials_review.png) show the approved fresh-green upland-village style. The scene is an art test rather than a canonical town map. Approved irrigation channels, stone terraces, an animated gate, a wooden bridge and a watermill extend this foundation; other village assets remain future work.

The first [animated stream-and-bank milestone](assets/terrain/eldenmere/stream/README.md) is approved following user review. Its [updated looping scene](assets/terrain/eldenmere/stream/review_scene.gif), [water-cycle close-up](assets/terrain/eldenmere/stream/water_cycle_review.gif) and [47-bank atlas](assets/terrain/eldenmere/stream/bank_47_review.png) use 24×24 tiles beside the approved ground and 24×36 characters. Six 200 ms phases animate local ripples while banks stay fixed; two surface variations share the same clock. This milestone establishes the water style before irrigation modules, terraces and working village props.

The [irrigation-channel milestone](assets/terrain/eldenmere/irrigation/README.md) is approved following user review. The [updated looping scene](assets/terrain/eldenmere/irrigation/review_scene.gif), [channel close-up](assets/terrain/eldenmere/irrigation/channels_closeup.gif) and [animated module board](assets/terrain/eldenmere/irrigation/modules_review.gif) show earth-lined 24×24 straights, bends, splits, stream inlets and trickling outlets. Directed currents use the approved water palette and six-frame timing; the channel walls stay fixed. The review extends the previous scene and preserves the existing approved assets.

The [stone terrace, steps and spillway milestone](assets/terrain/eldenmere/terraces/README.md) is approved following user review. Its [updated looping scene](assets/terrain/eldenmere/terraces/review_scene.gif), [enlarged terrace close-up](assets/terrain/eldenmere/terraces/terrace_closeup.gif) and [module board](assets/terrain/eldenmere/terraces/modules_review.gif) show warm fieldstone, a 24-pixel wall face, a four-tread 48×48 staircase and a six-phase spillway connecting the upper and lower irrigation. Stone stays fixed; falling highlights, impact flecks and ripples animate with the existing water clock. Characters on both levels establish scale.

The [irrigation gate](assets/terrain/eldenmere/gate/README.md) is approved following user review. Its [updated scene](assets/terrain/eldenmere/gate/review_scene.gif), [gate close-up](assets/terrain/eldenmere/gate/gate_closeup.gif) and [open/closed/jammed comparison](assets/terrain/eldenmere/gate/states_review.gif) show a small hand-lifted wooden sluice on the existing eight-pixel channel. Seven animations cover idle states, opening/closing and pin repair; delayed downstream art demonstrates restricted, stopped and restored flow. The new gate sits on the upper level, with the existing southern spillway carrying water down. The earlier terrace layout and asset files remain unchanged.

The [wooden bridge](assets/terrain/eldenmere/bridge/README.md) is approved following user review. Its [updated scene](assets/terrain/eldenmere/bridge/review_scene.gif), [bridge close-up](assets/terrain/eldenmere/bridge/bridge_closeup.gif) and [module comparison](assets/terrain/eldenmere/bridge/modules_review.gif) show an east–west crossing with a 48-pixel walking deck, repeatable middle sections, low timber rails and stone abutments. Both banks and the deck share the same elevation, with water below. Small lanterns and support wakes animate; the structure stays fixed. Separate foreground rails support character layering, and Caelan's unchanged right-facing idle shows scale.

The [watermill](assets/terrain/eldenmere/watermill/README.md) is approved following user review. Its [running scene](assets/terrain/eldenmere/watermill/review_scene.gif), [mill close-up](assets/terrain/eldenmere/watermill/mill_closeup.gif) and [running/stopped comparison](assets/terrain/eldenmere/watermill/states_review.gif) show a slate-roof stone-and-timber building, a level service landing and an eight-paddle wheel driven by the east-to-west race. Clockwise rotation agrees with the current; small left-side droplets and downstream ripples animate while the structure stays still. A blocked-supply alternative holds the wheel stationary. The directed race has a continuous falling grade, and existing artwork/story files are unchanged.

### Liam’s first lantern — MQ04 opening

After Aldric’s visit, speak with Tomas in the sanctuary courtyard. Join the school preparations, look at Liam’s drawing, agree on the outing with his mother, and accompany Liam and Tomas to Mira. Continue from Mira to the working mill, the Venn family and Elira’s memorial lantern. After Elira, collect the materials from Mira, take a break at Liam’s home, and bring his questions to Serene in the sanctuary hall. Return home to finish Liam’s personal lantern, carry it to his mother at school, then put it away safely. MQ04 completes after the final farewell; the finished lantern stays unlit at home for tomorrow’s festival. Existing PR3 saves continue directly from Serene without replaying earlier scenes. See [Liam’s lantern quest](docs/LANTERN_QUEST.md) and its [opening dialogue](docs/narrative/game_01/CH01_MQ04.md), [final section](docs/narrative/game_01/CH01_MQ04_PR4.md), and [actual-game finale preview](docs/reviews/lantern_finish/README.md).
