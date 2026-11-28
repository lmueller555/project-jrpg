# Iselin overhead contact and passing repair

This folder retains the ImageGen source work for phases16–31. The sibling
`../overhead_032_047_pose_retry` owns phases32–47. Final production registration,
the portable actor profile and native shot acceptance belong to the parent
Iselin exporter; neither folder changes gameplay or publishes an accepted bank.

`master.png` contains sixteen complete ImageGen drawings. `generation.json`
records the unchanged generation master, exact prompt and three reference-image
hashes. `reference_manifest.json` records the guide phases and actual anatomical
guide landmarks. The only appearance references are the approved head/hair/braid
crop and coat material crop; a full-body reference previously imposed one fixed
extended leg on the entire cycle.

The primary guide marks each linked hip→knee→boot chain, with anatomical right
in red and left in cyan. These are construction labels only. No guide pixels,
colors or labels become final artwork. A projecting knee can lie below the
crown while its calf folds back toward an above-crown boot. Distinguishing these
points prevents an advancing knee from being painted as a straight hanging shin.

`prepare_annotated_batches.py` reproduces these guide-only authoring inputs:

```sh
python assets/source/cinematics/fire_veinhold/bridge_ascent/characters/iselin/batches/overhead_016_031_pose_retry/prepare_annotated_batches.py --start 16 --stop 32 --name NEW_FOLDER
```

It refuses to overwrite retained prompts or masters. The guide uses one fixed
crop and uniform scale for every pose, not a fit to occupied height.

The earlier `key_master.png` tried phases16/24/32/40. It established opposing
contacts but left the phase32 passing boot too low. The subsequent
`passing_annotated_master.png` depicts phases0/8/24/32 with correctly exchanged
contacts and a bent-knee, folded-calf passing silhouette. Root provisionally
accepted these four source keys before the sixteen-pose expansion. This is
source-construction acceptance, not a completed native-playback review.

The guide geometry diagnostic in `guides_corrected` and
`build_corrected_key_guides.py` did **not** prove a stretched-leg defect. Explicit
local cylinder scaling produced the same projected shape as the original
dimension-based construction. The apparent low gray projection was the knee,
not the boot endpoint. Those diagnostic files are retained for traceability and
were not the input references for `master.png`.

`alpha_corner_audit.json` binds the raw master and measures the four 10×10 corner
patches and cell borders. All phase16–31 corners are alpha≤1 and every cell border
has zero alpha>16pixels. Native registration, batch joins and loop review remain
required; sixteen distinct PNG regions do not certify correct motion.

`selection.json` selects the later eight complete drawings in
`entry_016_023_bridge` for phases16–23. Those drawings use the actual corrected
phase15 and subsequent phase24 as motion bounds, preserving the compact entry
and gradually opening the left calf. The original16–23 drawings approached
contact too early and are retained as rejected history. The bridge's own raw
master, prompt, exact references and zero-alpha corner/border audit are retained
in that subfolder. Selected phases24–31 still use this folder's main master.
