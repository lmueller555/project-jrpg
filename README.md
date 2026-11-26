# Project JRPG

A Python/Pygame fantasy JRPG set in Auratia. The current playable opening
follows Caelan through ordinary household errands in Eldenmere and Mira's mill
adventure. Terrain uses 24×24 native tiles and the established pixel-art cast.

**Opening runtime retirement:** New Game now starts directly in Caelan's
bedroom. The old flashforward, regent relief/mining/rescue quest and Festival
of Light/lantern quest have been removed from gameplay, Gallery and Quest
Playtests. MQ01 and MQ02 remain, including their rewards, Mira's blade gift,
combat lessons, repairs and final cup placement. Dialogue now describes normal
household work and private remembrance rather than festival preparations or
an expected royal visit. Finishing MQ02 returns to exploration.

The [approved Fire Veinhold opening](docs/narrative/game_01/CHAPTER_01.md)
remains **future work**. This retirement does not add its prologue, soldiers,
royal arrival, fireball or invasion. The regional bridge is still physically
ruined and checkpoints remain closed; the planned initially intact bridge and
its later destruction require a separate implementation.

## Run the game

Use Python 3.10 or newer from the repository directory:

```sh
python -m pip install -r requirements.txt
python main.py
```

Paths resolve relative to `main.py`; no asset build is required. Use
`python main.py --windowed` for a window, or press **F11** to toggle fullscreen.
The 480×320 world uses crisp integer scaling; interface text renders at display
resolution with the bundled Atkinson Hyperlegible fonts.

Move with the keyboard, face nearby people and objects, and press **E** to
interact. **Space**, **E** or a click advances dialogue. **Esc** opens the pause
menu; **M** opens the regional map where available. Settings control display,
music/effects levels, text size, reduced motion and objective visibility.

The title's **New Game** starts the bedroom sequence. **Continue** loads a saved
journey. **Gallery** offers 20 retained independent studies, including the
morning, household visits, mill work, regional social scenes and the Ice Reaper
study. Replays use fresh sessions without changing Continue. See
[Gallery](docs/GALLERY.md) for entries and controls.

**Quests (Playtest)** offers only **MQ01** and **MQ02**, with separate manual-save
and autosave libraries. It does not expose retired MQ03/MQ04 fixtures. See
[quest playtests](docs/QUEST_SYSTEM.md#title-screen-quest-playtests).

## Current exploration and combat

Eldenmere, the upstream millrace and the surrounding Elden Vale remain
explorable. The Sanctuary reserve retains caretakers, visitors, memorial care
and its natural aether confluence. The cave retains treasure, encounters,
Vespermaw, the healing pool and its Aqua lesson, with no rescue mission,
injured-worker markers or automatic Mira/Lucan recruitment. Its purpose in the
future opening remains undecided.

A repeatable Bat west of Eldenmere's well provides optional combat before the
mill quest. The mill adventure teaches Guard and Caelan's first weapon
technique, then combines practical engineering with a modest water spell.
See [combat](docs/COMBAT.md), [MQ01](docs/narrative/game_01/CH01_MQ01.md),
[MQ02](docs/narrative/game_01/CH01_MQ02.md) and the
[mill implementation](docs/MILL_QUEST.md).

Save Game and Load Game provide ten manual slots and three autosave generations
per journey. Scene entry and completed battles trigger autosaves; party defeat
opens Game Over with manual-save/autosave loading. See
[save system](docs/SAVE_SYSTEM.md).

**Eldenmere** accompanies the village and millrace. **Kindled Courage** plays
in combat; ordinary exploration music resumes at its interrupted position.
The cave retains its exploration track. The retired New Game cinematic's
leitmotif is no longer registered or exported; original music uploads remain
source material. See [music files](assets/music/README.md).

## World and authoring references

The [narrative index](docs/narrative/README.md) routes story work to its existing
owners. The [World Atlas](docs/narrative/world/WORLD_ATLAS.md#approved-world-map)
and canonical classroom map place Elden Vale in southern Merovar and Adamanthra
in the far north. The longer journey, Worldveins, Carcovia's Veinholds and
Iselin's later arc remain approved direction rather than implemented quests.

Read [AGENTS.md](AGENTS.md) before contributing. Character work follows the
[sprite and animation standard](docs/SPRITE_ANIMATION_STANDARD.md). Prop work
also follows the [interaction standard](docs/OBJECT_INTERACTION_STANDARD.md)
and [personal-prop policy](docs/PERSONAL_PROPS.md). Terrain and room work use
[the terrain guide](docs/GRASS_TERRAIN.md) and the applicable
existing asset guides.

The [tool catalogue](tools/README.md) documents retained builders and captures.
Historical material under `docs/reviews/` preserves its original context;
old screenshots and commands do not imply that removed quests still run.
