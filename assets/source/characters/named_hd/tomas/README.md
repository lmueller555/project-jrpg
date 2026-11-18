# Native named identity and travel bank

Dormant opt-in48×72 native artwork. Logical size24×36, draw anchor[12,30],
ground anchor[12,34], original collision/schedule unchanged. Four walk phases
per direction at140ms preserve the original560ms two-step cadence.

The approved high-resolution concept/turnaround masters are retained in the
original actor source folder. The exporter directly samples them at the target
artwork density using original registration bands and material palette; it does
not enlarge old24×36 actor pixels. This deliberately preserves the exact existing
identity and body proportions. Front/left/right/back references are independent.

Walks use literal complete native contour drawings in `walk_drawings.json`.
The source head and limited identity-bearing costume-center panel are preserved
unwarped; native arms, legs, cuffs, silhouette and support/recovery contours are
redrawn. No old limb/part rig, runtime skeleton or sprite warp is involved.
Profile gait alternates both near/far legs with opposite arm swing. Front/rear
steps project in depth rather than kicking sideways. Four contact/passing keys
use the original frame budget; no duplicate interpolated frames are added.

Serene retains silver-templed brown bun, blue-gray mantle/bronze clasp, sage
calf-length dress, linen button apron/cuffs and brown boots. Tomas retains blond
hair/green eyes, rust vest/cream sleeves, dark trousers and the anatomical-left
knee patch (front viewer-right and left profile, absent on rear/right).

`portrait.png` is copied byte-for-byte from the existing72×72 dialogue portrait.
It already matches the original identity and is not upscaled/redesigned.

Run `python assets/source/characters/named_hd/tomas/export.py --repo-root .`
then `python assets/source/characters/named_hd/tomas/validate.py --repo-root .`.
Requires Pillow. `sha256.json` records all21 outputs; export is deterministic.
Native contour/identity contact sheets were inspected. Production movement,
scenery foot-locking and action-bank transitions require separate integration
validation before activation. No runtime, gameplay, story or party file changes.
