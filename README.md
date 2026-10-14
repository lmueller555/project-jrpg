# Project JRPG

An original Python pixel-art JRPG inspired by the visual language of 16-bit era classics.

The project's narrative and authoritative art guide live under [docs/](docs/).

## Run the Eldenmere world slice

Python 3.12+ recommended (Pygame must support your installed Python version).

```sh
python3 -m pip install -r requirements.txt
python3 main.py
```

The first playable **environment prototype** launches in Eldenmere Sanctuary. Walk to the doorway along the bottom of the room and press **E** to enter the village.

- **WASD / arrow keys:** walk
- **E / Space:** interact with nearby NPCs, signs, buildings and doorways
- **Esc:** close game

Explore the sanctuary, village square, bridge, watermill, the three Quest 1 household locations and a wayside shrine. This is a **world-layout and rendering prototype**, not an implementation of the authored quests or finished character art.

## Current vertical-slice constraints

- Native gameplay canvas: **320 × 224**; window: **960 × 672** (3× integer nearest-neighbor upscale).
- **16 × 16** map cells; **16 × 24** temporary humanoid render footprint.
- Settlement and interior maps are **editable JSON**:
  - `maps/towns/eldenmere.json`
  - `maps/interiors/sanctuary.json`
- Terrain, objects, collisions, NPC placement, labels and map transitions are data-driven.
- The initial visuals have been upgraded to a cohesive, deterministic **original pixel-art first pass** in `visuals.py` (cached native-resolution terrain textures, timber-and-stone architecture, pitched roofs, river highlights, farmland, character silhouettes). These remain **code-authored interim assets**, not final hand-polished production tilesheets or character animation sheets. The next art milestone is curated original PNG atlases with edge variants, intentional layering and directional walk cycles, consistent with [the art style guide](docs/ART_STYLE_GUIDE.md).
- Collision and doorway behavior are first-pass. The map is a **layout sketch**, not a finalized geography, floorplan or navigation system.
- Quest dialogue, companions, triggers, battles, save data, menus, final animations, sound and music are **not implemented**.

To validate map structure without Pygame, run:

```sh
python3 -m unittest discover -s tests
```

## Story references

- [Chapter 1](docs/narrative/game_01/CHAPTER_01.md)
- [Quest 1 narrative specification](docs/narrative/game_01/CH01_MQ01.md)
- [Game I act outline](docs/narrative/game_01/ACT_OUTLINE.md)
