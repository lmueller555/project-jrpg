# Machinist combat art

Both source atlases were authored with `image_gen.imagegen` on 2026-11-02.
The complete generation prompts and reference are retained in `generation.json`.
Mira's atlas is an imagegen edit of the existing Mira source, preserving her
brown bob, white flower, pink blouse, belt, trousers, boots and proportions while
replacing every battle spear with a short spring-powered bolt launcher.
Rivet's atlas is original generated art for the small four-legged workshop bot.

Rebuild the production assets from the retained sources:

```sh
python tools/build_machinist_assets.py
```

`python tools/build_mill_combat_assets.py` also invokes this exporter before
exporting the Tusker. It cannot restore Mira's historical spear atlas or prop.
The exporter only extracts connected authored alpha regions, thresholds alpha,
applies one nearest-neighbor scale per actor, and registers the ground anchor.
It does not draw character anatomy, equipment, poses, or effects. Each runtime
manifest records the source SHA256 and source bounds for every pose.

Mira uses a 4-column, 5-row source layout: idle 0–1, bolt shot 2–4, guard 5–6,
hurt 7–8, victory 9–10, defeat 11–12, walk 13–15, overclock 16–18, and the
isolated world launcher prop 19. Runtime characters use a 64×64 canvas and
ground anchor (32,54). Bolt shot lasts 800ms with contact at 400ms; overclock
lasts 900ms with the controller-command pose active at its 500ms application.

Rivet uses a 4-column, 4-row layout: idle 0–3, deploy 4–5, piston jab 6–8,
overclock 9–11, victory 12–13, suspend 14–15. Its 32×32 canvas and ground anchor
(16,28) keep it visibly smaller than Mira. Piston jab lasts 800ms with contact
at 400ms, during the authored extended-piston pose. Suspension is a folded,
dimmed machine, without a damaged or defeated state.

`runtime_motion_preview.gif` assembles the exported native frames for visual
review. The runtime folder contains the authoritative individual frame files.
