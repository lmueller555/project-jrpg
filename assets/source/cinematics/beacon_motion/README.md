# Opening beacon scene — walking and mechanical work

These retained imagegen masters provide new motion for the opening cinematic.

- `walk_left_generated.png`: four successive left-facing walking poses for
  Caelan and four for Mira. The opposite contacts use opposing near-arm swings;
  passing poses keep the hands close to the hips. Their existing clothing,
  silhouettes and Mira's ponytail/cream flower remain the design references.
- `mira_repair_generated.png`: right-facing standing, lowering, preparation,
  two wrench-working poses and finishing. The lamp was removed with imagegen
  so the game can display its independently changing restoration states.

Run `python tools/build_beacon_motion.py` from the repository root. Pillow and
NumPy are build dependencies; runtime rendering uses only the exported PNGs.
The exporter performs isolated-cell crops, transparent-matte cleanup,
nearest-neighbor resizing at one physical scale per actor/sheet, and placement
on a 96×112 canvas with floor anchor `[48,104]`. It does not stretch limbs,
interpolate body parts or alter retained source pixels.

`assets/story/opening_cinematic/actors/beacon_motion/manifest_fragment.json`
contains the pose, loop, transition, source-hash and extraction records for
integration into the existing actor manifests. Fragment image paths are
relative to each existing actor folder. Standing bodies are approximately
80 native pixels high; Mira's kneeling work remains around 60 pixels high.

The walking cycle uses four authored frames at 180 ms each. Mira's repair
cycle alternates wrench contact with a brief repositioning pose. At the
registered repair root `(585,375)`, the two extended wrench tips reach
`(620,353)` and approximately `(618,355)`, contacting the left frame of the
separately authored lamp. No lamp, sparks, ground or shadows are baked into
these actors.

The exporter also writes a development contact sheet under `work/`; it is not
a runtime dependency. Original character PNGs and existing actor manifests
are outside this exporter's ownership.
