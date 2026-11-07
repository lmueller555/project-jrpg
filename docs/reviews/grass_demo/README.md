# Playable grass demonstration

![Grass demonstration](contact_sheet.png)

[Full field](overview.png) · [Walking, running and standing](grass_walk.mp4)

![Grass height compared with Caelan](height_comparison.png)

The height study places unoccupied grass and Caelan on one visible ground
baseline at the same enlargement. It measures the opaque pixels, not the
transparent sprite canvases. The gameplay photographs separately show the
short foreground blades covering legs while the torso stays readable. Every
occupied movie frame is also compared with grass drawing disabled: opaque
head and torso pixels must remain identical, while leg overlap is observed.

This isolated prototype uses the actual game Player, camera and World rendering.
The review walks and runs through authored grass patches, holds still while the
grass remains displaced, then leaves it to recover. Every review position is
reached through ordinary movement; no character poses or bend states are staged.

The deeper emerald palette and lawn, meadow and woodland materials remain in
the demonstration. Eldenmere and the Sanctuary have not received the new pack.
The launcher never opens game journeys or settings files.

Run `python tools/preview_grass.py` to explore. Use WASD or arrows to move,
Shift to run, R to reset, M for reduced motion and Escape to exit.

Regenerate with `python tools/capture_grass_demo.py`; verify retained source,
artifact and original-world hashes with `python tools/capture_grass_demo.py --check`.
The [verification record](verification.json) contains actual positions, occupied
grass states, recovery, timings and the immutable source fingerprints.

The revised height study measures **34 visible pixels for Caelan** and
**16–17 pixels for unoccupied grass**, or **47–50% of his height**. Every idle
and directional parting pose stays within that limit. The shorter foreground
layer allows the grass to overlap his legs while preserving his coat and belt.
Across the actual walkthrough, **64,632 opaque upper-body pixel comparisons**
show **zero occlusion**, while leg overlap appears in **186 frames**.

The final silent video contains **899 frames over 44.95 seconds**, at
**960 × 640 / 20 fps**, and the review retains 19 actual movement/standing views.
Walking, stronger running displacement, held occupancy and recovery after exit
all pass. Original-world reference hashes and source/artifact checks pass;
a deliberately stale source fingerprint was rejected. The height board and
standing/running views were visually inspected after the emerald palette and
shorter vegetation were applied. Existing game maps retain their original grass.

The focused interaction, playable-demo and asset-proportion suites pass:
**19 tests and 381 subtests**. Deterministic asset and scene build checks also pass.
