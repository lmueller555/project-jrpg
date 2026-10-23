# Sanctuary interior source — review

This first sanctuary interior pack supports the approved opening's bedroom,
breakfast, request and return scenes. Three retained transparent prop atlases
provide eighteen new native props. `recipe.json` records their exact source
crops, hard-alpha sampling, materials, positions, furniture parents, access
points, story roles and proposed room links. `parts/` retains every native
sample and the small steam glyph reused from the approved cottage smoke.

The separate expanded room maps have 10×10, 12×10 and 16×10-tile floors:

- **Bedroom:** family drawing, unfinished reading, copied notes, bed, wardrobe,
  a clothes chest, patched belongings, desk chair, boots, basin and a plant.
- **Shared hall:** a quiet reading nook, bookcase, benches, community notices,
  mending table, herbs, everyday closed records and a place to wash and leave boots.
- **Kitchen/dining:** three breakfast settings, bread and kettle, pantry and
  hearth, with distinct medicine, food/oil and care bundles for the three homes.

The tone is ordinary warmth, ongoing care, curiosity and family belonging.
Six bedroom inspection lines are copied verbatim from the approved S01 script
in `docs/narrative/game_01/CH01_MQ01.md`. New visual interpretations and room
layouts remain review proposals; they add no required inspection checklist,
named NPC design, religious doctrine, future warning text or plot revelation.
See `design.md` for the story rationale and staging notes.

Architecture, native furniture, kitchen pieces, benches, herb box and fire
frames are read from approved packs without rescaling or modifying their files.
Window light repeats in 5.4s, fire in 1.2s and kettle steam in 1.8s. Thirty-six
300ms steps form the shared 10.8s timeline. Containers, furniture and actors stay
fixed. Steam moves only the copied puff glyphs above the fixed kettle spout.

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/project-jrpg/bin/python tools/build_eldenmere_sanctuary_interior.py
PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/project-jrpg/bin/python tools/test_eldenmere_sanctuary_interior.py
```

Every prior asset and narrative input remains read-only. This is a furnished
art/layout review. Room transfers, doors, dialogue triggers, quest state,
sleeping/sitting poses, audio and the remaining cast require game integration.
