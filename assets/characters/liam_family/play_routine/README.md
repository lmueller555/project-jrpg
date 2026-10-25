# Liam and Daisy — playtime actions (awaiting review)

Four unique hard-alpha poses per action, using the approved character palettes:

- Liam: `invite_left/right` (500 ms per pose); `settle_bed` (300 ms per pose);
  `leave_bed` (220 ms per pose). 96×96 canvas, anchor [64,66]. His approved
  24×36 idles/walks/runs are padded at [52,36] without changing native pixels.
- Daisy: `hop_left/right` (140 ms per pose) and `wag_left/right` (180 ms per pose).
  64×48 canvas, anchor [32,42], native offset [16,12]. Directional markings come
  from their own approved idles. Her existing stand/settle actions connect to
  these new poses, with all four existing walks/runs reused for travel.

The hops repeat twice with whole-body lift, ear follow-through and a fixed
shadow. The wag lasts 1.08 seconds, with its root joined to her body.
Liam's bed action stays registered to the walkable bedside [88,246], drawing
above the bed. His resting head is on the pillow at [60,225]; the approved quilt
and footboard pixels cover his lower body. The resting pose is held until wake.

`animations.json` records frame timing, retained source layers, landmarks and
SHA-256 hashes of all existing Liam and Daisy PNGs. Build with
`python tools/build_liam_daisy_play.py`; the family-home builder also invokes it.
See [actual runtime previews](../../../../docs/reviews/liam_daisy_play/README.md).
