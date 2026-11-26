# Prologue golden eagle — complete cinematic poses

The two original image-generated sheets and exact prompts are retained here.
Each cell is a complete anatomical drawing, viewed from above and behind:
brown body, tawny-gold nape, two connected fingered wings and tucked feet.
The chronological flight sheet supplies sixteen complete power-flight poses;
the companion sheet supplies a finite gentle-left-bank and recovery.

`recipe.json` pins source hashes, body landmarks, fixed source scales and
sequence timing. Export uses whole-cell crops, uniform nearest-neighbour
sampling, chest registration, generation-matte removal and one shared palette.
The changing wing bounds never determine scale or placement. No separated
wing/body rig, limb rotation, mesh warp or generated intermediate is used.

Runtime frames are 256×256 RGBA with chest anchor `[128,144]` and artwork
density 2: the cinematic presents a 128×128 logical frame, preserving detailed
artwork at the 960×640 display. Typical maximum wingspan is around 190 artwork
pixels, or 95 logical pixels. This is newly authored hero art, independent of
the small regional birds.

The 750 ms flap cycle has fourteen 47 ms exposures and two 46 ms exposures.
Its phase offsets are 391 ms for the first flight window and 141 ms for the
power-climb window. The bank uses eight 375 ms exposures across three seconds;
its entry and exit reference the exact complete level-wing `flap_04.png`.
Glide alternates two complete compatible level-flight poses. These shared
neutral endpoints preserve the pose across the shot's action boundaries.

Reproduce the exports with the project art dependencies installed:

```sh
python tools/build_prologue_eagle.py
python tools/build_prologue_eagle.py --check
```

`assets/story/fire_veinhold_opening/shot01/eagle/animation.json` owns the runtime
canvas, density, anchor, sequences and timing. The adjacent export provenance
records palette, source hashes, crop/scale/registration and output hashes.
Scene paths, camera, wingbeat sound and Gallery integration belong to the shot
controller, rather than this asset exporter.
