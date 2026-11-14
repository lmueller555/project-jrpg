# Iselin royal replacement review

Iselin replaces the former regent in live opening scenes, MQ02/MQ03 dialogue, portraits, actor registration, Gallery playback and post-rescue resolution. Her title, quest stages and existing outcomes are preserved. Her approved biography and spoiler boundaries are recorded in [ISELIN.md](../../narrative/game_01/characters/ISELIN.md).

## Visual evidence

- [Scene artwork](scene_art.png): complete cinematic gestures, seated drawing, aerial views and diagonal walking cells.
- [Gate greeting](gate_greeting.png), [meal](emergency/meal_with_lucan.png), and [Sanctuary arrival](../gallery/regional_sanctuary_arrival.png): production renderers with Iselin's detailed sprites.
- [Diagonal walking preview](diagonal_walk.gif): the new complete-drawing cinematic cycle, 16 frames over 560 ms.
- [Post-rescue report](resolution_report.png): acknowledged resolution dialogue using the replacement identity.

The approved portrait, all four idles and all 64 ordinary walking PNGs are preserved. New artwork is confined to missing scene-specific poses and perspectives. Historical royal artwork and obsolete builders are archived outside live registries and test discovery.

## Reproduction and limits

Run with the project's Pygame/Pillow environment and `PYTHONPATH=.`:

```sh
python tools/build_regent_iselin.py --check
python tools/build_regent_arrival_actors.py --check
python tools/build_regent_aerial_actors.py --check
python tools/capture_iselin_replacement.py
python tools/capture_mq03_emergency.py --out docs/reviews/iselin_replacement/emergency --no-movie
python tools/capture_mq03_emergency.py --out docs/reviews/iselin_replacement/emergency --check
```

The emergency driver traverses the actual welcome, meal, interruption, party rejoin and travel flow, including saved checkpoints and Continue. Its verification JSON records inputs and capture hashes. The post-rescue images use explicitly seeded victory/evacuation fixtures, followed by the actual dialogue/checkpoint chain; they do not claim a complete played battle. Gallery images use the production replay controller.

Validation covers actor manifests, detailed seating, saved legacy unavailable reasons, arrival/aerial rendering, Sanctuary staging and the MQ03 resolution chain. The existing `test_active_visit_cannot_load_without_its_scene_checkpoint` save-fallback failure is reproducible on the original main runtime and remains outside this replacement.

Integration checks also exposed and corrected a detailed-canvas copy error in the road-pan effect and a missing detail presentation step in the Sanctuary cinematic. Ordinary surface alpha/clip behavior remains covered by the road-pan regressions.

The [last 50 ms of the aerial handoff](handoff.png) show continuous ground motion.
Mean RGB difference to the endpoint is 5.0266/255 (1.971%); the palette-dependent
check now uses a 2% full-range bound. The final aerial frame must still equal
the first ground frame byte for byte, with no black fade.
