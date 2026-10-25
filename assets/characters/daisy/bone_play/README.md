# Daisy's bone-play actions — approved

All action bodies are transparent 64×48 frames with draw anchor [32,42].
The approved 32×36 walk/idle pixels are padded at [16,12]; lying art is padded
at [12,12]. Existing character PNGs and the original palette are unchanged.

`animations.json` separates the dog body (`file`) and bone overlay (`bone_file`).
The runtime draws the bone overlay only when Daisy owns the single toy. Each
frame records `bone_local`, visibility, orientation and retained source paths.
Near-jaw and paw pixels mask the bone at contact. Back carrying has a completely
transparent bone overlay, while its ownership and location remain tracked.

- `pickup_left` / `drop_left`: four 220 ms poses, contact at frame 2 (zero based).
  Contact mouth [22,41] has feet offset [-10,-1]; a floor center [138,259]
  therefore pairs with an even-grid approach [148,260]. The head bends around
  the neck to reach the floor without lengthening the neck or arms.
- `play_bow`: four 180 ms poses, a restrained front-chest dip with fixed hips.
- `shake_left`: four 150 ms poses, short head movements and ear follow-through.
- `chew_left`: four 220 ms lying poses. The bone is braced at [20,45], feet
  offset [-12,3], between the front paws. Body and paws remain grounded.
- `settle_bone`: four 220 ms poses; frame 3 transfers mouth to paws.
- `rise_bone`: four 220 ms poses for getting up from the rug.
- `release_paws`: four 200 ms poses; frame 2 leaves the bone at the same paw spot.
- `nudge_left`: four 180 ms poses; frame 2 nudges the floor bone two pixels left
  to [18,45], preserving the even-X/odd-Y floor pickup registration.
- `carry_walk_front/left/right/back`: approved four-frame 140 ms walks with
  mouth-following bone overlays. `idle_frames` holds separate static poses.

Build with `python tools/build_daisy_bone.py`. All flattened bodies and overlays
reconstruct exactly from the recorded layers; `approved_png_sha256` protects
pre-existing Daisy PNGs and excludes this new pack to keep rebuilds stable.
