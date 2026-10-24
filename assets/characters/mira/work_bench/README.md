# Mira — outdoor bench routine

Status: **awaiting user review**. This adds a dedicated 24×36 work animation; the approved idles, walks and workshop art remain unchanged.

An eight-second loop contains nine distinct poses and 21 timed steps: pause with hand on hip, lean toward a small repair fitting, raise the wrench, make **three broad strokes**, lower the wrench, test the fitting's handle by hand, straighten and pause. The wrench grip travels more than six native pixels between its high and pulled poses. Pauses bookend the work; this is not a rapid hammering cycle.

The approved left-facing head retains Mira's ponytail, cream flower on anatomical left, and profile eye. It is combined with a planted stance from her approved back appearance and explicitly posed pink sleeves and bare forearms. Head and shoulders lean together by one or two pixels; the boots remain fixed. The bench is unchanged. A separate 12×9 fitting layer turns its small bright handle during the testing phase.

- `animation.json`: variable-duration pose sequence and synchronized fitting references.
- Named pose PNGs: transparent, native 24×36 sprites, draw anchor `[12,30]`, art foot anchor `[12,34]`.
- `fitting_*.png`: separate bench-top repair fitting states.
- `spritesheet.png`, `poses_review.png`: native and enlarged pose contact sheets.
- [Enlarged looping close-up](../../../../docs/reviews/mira_bench/bench_closeup.gif) and [workshop scene](../../../../docs/reviews/mira_bench/workshop_scene.gif): captured from the running game's renderer, with exact pose durations and opaque RGB backgrounds.

Mira stands at ground-probe center `[610,448]`, beside the right corner of the exterior bench, facing left toward the fitting. Her small stationary foot collider is 8×4; the original 24×12 player probe is unchanged. Both approved yard approach points and the workshop doorway remain reachable. She stays outdoors; entering and returning from the shop preserves the same actor and the work clock. There are no fetching trips, dialogue or quest effects in this milestone.

Rebuild with `python tools/build_mira_bench.py`, then capture with `python tools/capture_mira_bench.py` using the asset environment (Pillow and Pygame). The recipe and reconstructable appearance/arm/tool layers are retained in `assets/source/characters/mira/work_bench/`. The runtime requires only Pygame and the checked-in exports.
