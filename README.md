# Project JRPG

Explore the approved Eldenmere town as Caelan by running `main.py`. The game uses the new 24×24 terrain and 24×36 character art, with live movement, collision, a following camera and animated scenery. The retained story and asset tooling are documented below.

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
menu**. Click New Game to begin Caelan's opening morning, or use arrows and Enter.
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
foreground cascades. The soundtrack is now a new 93-second sampled piano/cello
theme in 4/4 at 72 BPM, with strict beat alignment. The earlier flute/harp track
has been replaced. Listen to the [clean and metronome-reference excerpts](docs/reviews/title_piano_cello/README.md)
or watch the [title video and water close-up](docs/reviews/title_water_music/README.md).

| Control | Action |
| --- | --- |
| WASD or arrow keys | Move Caelan |
| Shift | Run |
| M | Open/close the town map; click landmarks to inspect them |
| J | Open/close the quest journal; select a quest and scroll its details |
| Left click anywhere / Space / E | Advance an open conversation |
| E near a bedroom furnishing | Inspect it when the prompt appears |
| Click a response button | Accept a quest or leave it for later |
| F11 | Toggle fullscreen |
| Escape | Close the journal/map, or pause/resume |

The resizable window uses crisp integer pixel scaling. Explore the full approved 64×56-tile layout, both brook bridges, the sanctuary and eastern terrace stairs, all six cottages, the watermill, workshop and commons. Buildings, water, terrace walls and solid props block movement; roofs, trees and bridge rails draw at the appropriate depth. Water, the mill wheel, chimney smoke, lanterns and existing vegetation animate.

The commons now contains a roofed stone well, a rounded dirt-and-stone square and a southern path connection. The well has solid collision, roof occlusion and subtle water glints; the map labels this area **Well square**. The [updated town layout and in-game previews](docs/reviews/eldenmere_well/README.md) are approved by the user.

**Building doors open automatically when you approach.** They stay open nearby and close as you move away. Walk into an open doorway to enter; walk down through the interior's entrance threshold to return outside. No action key is required. The sanctuary hall also connects to Caelan's bedroom and the dining room through its northern doors.

All nine buildings have separate furnished interiors. Cottages use the approved 10×10, 13×10 and 16×10 layouts; the sanctuary uses its three approved rooms. The workshop and mill workrooms reuse the approved furniture and interior kit. Rooms include furniture collision, ambient lighting and hearth/steam animation where present. Smaller rooms are centered in the viewport, and M still shows the town map while indoors. The map's north and south roads currently end at the town boundary.

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
Mira/gardener conversations remain future work.

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
Portrait bubbles stay within the screen and their response buttons move with
them. The breakfast invitation, inspections and accepted-quest conversation
allow free movement. Walking away from the invitation leaves breakfast available
through **E: join breakfast** near the table or a later dining-room visit.
Getting out of bed and the guided sitting/meal/standing actions still control
Caelan's body; four-pose actions finish even when prose is advanced quickly.
Pressing a movement key while seated finishes the gestures and stands him up,
so unread dialogue never holds him at the table.
**Escape** opens a modal pause menu during exploration, dialogue or actions.
Journal, Map and Settings are available there alongside Resume and Quit; the
controls reference is inside Settings. Pausing holds NPC, action, camera and
ambience clocks. Music and effects have separate sliders with percentage displays,
mouse adjustment and
left/right or +/- keys. Settings also provides 100%, 125% or 150% text, reduced
interface motion and objective-tracker visibility. Preferences persist in
`saves/settings.json` independently of the journey.

Exploration uses a brief location plaque and nearby interaction prompts instead
of a permanent controls strip. Dialogue choices show hover/pressed feedback,
and menus use the same lantern selection mark, spacing and panel treatment.

Continue preserves the opening checkpoint without replaying finished scenes.
Saves from before this opening was added keep their existing location/progress;
choose **New Game** to experience the new beginning. See [story implementation](docs/STORY_IMPLEMENTATION.md).

The actual Halden sack, Elira lantern and Venn gate tasks, and Tomas's temporary
following segment remain the next story implementation. Visiting their houses
never marks those tasks complete. See [quest integration](docs/QUEST_SYSTEM.md).

The launcher automatically checkpoints quest/conversation changes, room transfers,
and exit to `saves/journey.json` beside `main.py`; the local saves folder is ignored
by Git. **Continue** restores quest facts, dialogue history and player location
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
- [Saga bible](docs/narrative/saga/SAGA_BIBLE.md): overarching narrative and multi-game boundaries.
- [Revelation plan](docs/narrative/saga/REVELATION_PLAN.md): player knowledge and disclosure constraints.
- [Game I story bible](docs/narrative/game_01/STORY_BIBLE.md): game-level requirements and an earlier alternative premise.
- [Game I act outline](docs/narrative/game_01/ACT_OUTLINE.md): the proposed direction, *The Broken Covenant*.
- [Chapter 1: Life in Eldenmere](docs/narrative/game_01/CHAPTER_01.md): approved opening structure.
- [Opening quest: A Day Like Any Other](docs/narrative/game_01/CH01_MQ01.md): approved first-quest narrative and dialogue.

These documents retain their original status labels. Approved story decisions, proposals, and open questions remain distinct; the reset does not change narrative canon.

## New character art

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
