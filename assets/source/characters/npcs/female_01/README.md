# Female NPC 01 — front-idle source

Status: draft appearance awaiting user review.

`idle_front_concept.png` is the generated appearance reference for the first female NPC: dark hair in a low bun, a plain short-sleeved blue dress with a defined waist and flared calf-length skirt, and brown ankle boots. The male NPC and Mira supplied only game style/scale references. The low bun is mostly hidden behind the head in this front view, with small dark nape contours.

`export_idle.py` exports a native transparent 24×36 frame. It thresholds alpha at 128, samples with nearest-neighbor, registers the head, shoulders, waist, hem, calves and ankle boots to fixed native rows, and maps colors to named material ramps. The chin/neck uses skin shades so source shadows do not become hair colors. `export.json` records source bounds, vertical registration, palette and material rules.

Rebuild from the repository root with the asset dependencies installed:

```sh
python assets/source/characters/npcs/female_01/export_idle.py
```

The export also writes a 24× review image, a 16× comparison with male NPC 01 and Mira, and four non-overlapping appearance layers under `layers/`. These layers reconstruct the idle; they are not articulated walking parts. The dress will need dedicated skirt poses later.

This work contains only the first front-facing idle. Other facing appearances, palette variants and walking frames will follow user approval.
