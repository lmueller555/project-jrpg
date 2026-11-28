# Bridge ascent guard artwork

The selected inputs are complete ImageGen-authored figures. The source artwork
is ready for the parent shot's native composition review; source inspection
alone does not establish final scene readability or physical foot locking.

`frozen_60_master.png` contains four distinct frozen guards and ice columns at
a high oblique view. The original raw PNG remains unchanged. Its prompt and
generation record retain the approved frozen-bridge reference and exact hashes.
The painted scene mapping is:

| World ID | Painted pose | Bridge-local position |
| --- | --- | --- |
| `carcovian_guard_1` | `left_back` | `[3.2, 0.7, 0.1]` |
| `carcovian_guard_2` | `right_mid` | `[-2.5, 1.6, 0.1]` |
| `carcovian_guard_3` | `left_front` | `[1.2, 3.0, 0.1]` |
| `carcovian_guard_4` | `right_back` | `[-4.6, 0.6, 0.1]` |

This follows the approved painted layout rather than the superseded procedural
pose indexes. The camera owner reuses the existing frontal cutouts during the
brief low-angle visibility and these new complete figures when they reenter
the wide picture. Each new frozen figure already includes its ice; an added
oversized ice shell would duplicate that silhouette.

`live_cycle_master.png` contains sixteen complete drawn poses in a 4×4 atlas.
The full two-step cycle lasts 800 ms, with 50 ms per drawing. These background
troops travel toward bridge-local −Y, up the final picture: their anatomical
right sword appears on image right and their left forearm shield on image left.
Their bowed, crown-dominant helmet views resolve the rejected contact study's
down-facing visor interpretation. All figures retain dark gunmetal plate,
charcoal cloth, aged copper trim and the current Carcovian emblem.

The source uses one uniform armor family. The scene supplies staggered phases,
spacing and gate emergence for the eight soldiers. At the intended few-pixel
size, separately authored subtle kit variants would not add a reliable read.

`live_source_art.json` selects all sixteen raw cells. A single fixed density
and internal ground root serve the whole bank; source silhouettes are not fitted
to occupied height. Export only extracts complete source cells and removes
alpha values of 16 or less. No body parts are shifted, warped, recolored or
blended. Both selected atlases retain transparent padding around every cell,
including the complete crystal apexes and weapons.

`authoring/build_live_pose_guides.py` and its rendered guide snapshots provide
camera and phase references to ImageGen. These simple mannequin pixels never
enter the final exports. Material-only armor crops avoid imposing a frontal
body or ice-stasis pose on the new run. `reference_crops.json` records their
source windows. Earlier contact-study art and its exact references remain
historical authoring evidence and are not selected for production.

Reproduce the exported inputs with the game's Python environment:

```sh
python tools/export_prologue_ascent_guards.py
python tools/export_prologue_ascent_guards.py --check
```

The runtime authoring inputs are under
`assets/story/fire_veinhold_opening/shot08/guards/`. `guardperformance.json`
declares the actual twenty PNG hashes; `provenance.json` binds the exporter,
raw atlas hashes, source cells and registration facts. The shot's player streams
the final composited movie bank rather than decoding these actor inputs.

`native_cycle_proof.png` shows the sixteen source poses at 2, 4, 8 and 16 native
pixels per metre, using whole-image premultiplied-alpha sampling. It is an
isolated diagnostic on a neutral bridge-colored field, not the final scene.
The parent shot review owns actual lighting, occlusion, scale, source switches,
world placement and motion acceptance.
