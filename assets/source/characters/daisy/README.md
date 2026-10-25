# Daisy — retained directional source

`idle_turnaround_concepts.png` is the generated appearance plate: front at top
left, left profile at top right, right profile at bottom left, back at bottom
right. The complete silhouettes and tails have transparent margins on every
side. The original generated source remains unchanged.

`tools/build_daisy_idles.py` exports each view using its registered crop, nearest
sampling, alpha threshold 128 and a limited shared palette. `export.json`
records the crops, occupied rectangles, eye/nose landmarks, layer ranges and
common foot anchor. Three full-frame retained layers reconstruct each native
idle exactly under `idle_DIRECTION_layers/`.

The dog canvas is 32×36. Front/back are 24 visible pixels tall and profiles 23,
slightly below Liam's 26. The wider transparent frame accommodates a natural
quadruped silhouette and whole fluffy tail. Both eyes are explicitly registered
in front, one in each profile, and none in back. The builder verifies frame
bounds, hard alpha, palette membership, eyes, baseline and layer reconstruction.

Requested facts are Daisy's name, family association, female pronouns, gray
coat with white/black spots, fluffy tail, floppy gray ears, and size slightly
smaller than Liam. Specific spot placement and these idle designs are proposed
for review. Left/right spots are intentionally asymmetric and stay associated
with the correct anatomical side.
