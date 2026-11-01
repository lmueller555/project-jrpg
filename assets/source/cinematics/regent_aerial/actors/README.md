# Aldric aerial opening: bird and convoy subjects

These are original imagegen-authored transparent sprites for the bird-led aerial
opening. Original generations are retained unchanged; `prompts.json` records
their exact prompts and the existing cinematic actor references.

- `bird_generated.png`: the same natural brown kestrel in six north-facing
  dorsal wingbeat poses, followed by left- and right-bank poses. The native
  export uses a 96×96 canvas and a torso pivot at `[48,48]`.
- `convoy_generated.png`: overhead and high-oblique rear-three-quarter views of
  Aldric, the cinematic gate guard and the complete horse/provision wagon. Each
  wagon view contains exactly one seated driver. The guard matches the existing
  cinematic's open steel cap, slate/navy tunic and spear.

The raw bird wing silhouettes cross nominal grid-column boundaries. The
exporter isolates each whole connected alpha subject rather than cutting a
uniform grid. A binary alpha threshold removes low-alpha matte colors without
painting, retouching or changing the subjects' colors. All six wingbeat frames
share one scale; head/tail body-axis registration holds the torso steady while
the wings move. The two bank frames have fixed torso pivots.

Overhead humans are deliberately foreshortened. They retain 48×64 canvases and
the common ground anchor `[24,56]`; the oblique bodies have the same appearance
from the lower camera angle. Both caravan poses use 160×160 canvases and anchor
`[80,128]`. They expose the horse, canvas roof, rear cargo and wheel footprint
from the aerial camera instead of reusing upright side sprites.

```sh
python tools/build_regent_aerial_actors.py
python tools/build_regent_aerial_actors.py --check
```

Exports live in `assets/story/regent_aerial/actors/`. `manifest.json` maps actor
IDs to per-actor `animation.json` files using the game's existing canvas,
anchor, pose and timed-loop format. The bird supplies `flap_north`,
`glide_north`, `bank_left_north` and `bank_right_north`; the convoy subjects
supply `overhead` and `oblique`. Runtime may rotate the north-facing art to
follow its geographic heading. Existing ground cinematic actor art is untouched.

`provenance.json` records all source and export hashes, subject bounds,
registration anchors and uniform scale factors for deterministic rebuilds.
