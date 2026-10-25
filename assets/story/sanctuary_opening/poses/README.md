# Sanctuary opening poses

Native transparent 24×36 breakfast bodies reuse the approved Caelan/Tomas
profiles. Heads and shoulders drop together by three pixels; compact bent knees
and boots retain the shared foot baseline. Tomas faces left; Caelan faces right.
The four plate-push frames pivot two short arm segments, reaching only two pixels.
The separate 8×4 plate moves by two pixels in contact with his wrist.

The head-only sleeping sprite keeps Caelan's approved hair/face and closes both
eyes. Place its image at `[48,123]` over the existing bedroom bed `[36,108]`;
the original quilt covers the body. The scene must suppress the standing body
while this overlay is shown, then restore Caelan at the clear bedside.

All body frames use draw anchor `[12,30]`. Suggested table positions and hand
landmarks are in `recipe.json`. The scene owns temporary furniture registration
and foot collision during the locked breakfast scene. The exports never change
the ordinary standing/walking artwork or approved furniture images.

Rebuild with `python tools/build_sanctuary_opening_poses.py` (Pillow required).
The builder checks hard alpha, source palettes, distinct motion poses and the
source PNG hashes. Runtime uses only the checked-in PNGs.
