# Eldenmere bank reeds — approved

One tall seeded reed clump and one shorter green variation extend the village foliage. Narrow olive leaves, airy silhouettes and warm brown seedheads use the approved foliage and cottage-wood colors.

| Asset | Transparent frame | Ground rectangle | Visible source height |
| --- | --- | --- | --- |
| Tall | 24×48 | `[0,24,24,24]` | 36 pixels |
| Short | 24×24 | `[0,0,24,24]` | 21 pixels |

Each directory contains `idle.png`, nine `frames/`, a horizontal `sheet.png`, fixed `base.png`, three source-derived `bands/` and `reeds.json`. Draw the translated bands, then the fixed base. Complete heads/tips and stem sections bend at most one pixel east; the roots never translate. Both variations share the existing 5.4-second breeze, using nine 600 ms poses with a held gust and settling pause. The metadata marks these as nonblocking dry-bank decorations; this does not add engine collision behavior.

Review files:

- `banks_closeup.gif` / `.png`: 3× stream, mill and terrace-channel view containing all seven new instances.
- `review_scene.gif` / `.png`: full existing scene at 2×.
- `reeds_review.gif` / `.png`: both designs at 12×, plus unchanged Caelan and both reeds at matching 6× scale.
- `scene_frames/`: 54 native 768×1296 frames at 200 ms, retaining the 10.8-second shared repeat.

Four tall and three short instances are placed sparingly on dry grass along existing banks. Instance phases vary without changing wind direction. Full ground anchors are dry; all animated pixels leave the waterline, bridge, gate, mill, paths, characters and previous plants clear. Existing water routes/elevations and every prior animation track are preserved. These are illustrative asset-review placements, not a finished level. GIFs use lossless frame differences, and held poses may merge while retaining exact timing.

Rebuild with `python tools/build_eldenmere_reeds.py`; verify with `python tools/test_eldenmere_reeds.py` in the documented Pillow environment. Source/sampling, animation and placement settings live under `assets/source/terrain/eldenmere/reeds/`. Both reed designs and their animations are approved for main.
