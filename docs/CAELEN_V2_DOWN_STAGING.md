# Caelen V2 — Downward animation staging

The 32×48, five-frame (160×48) **native prototype** is available in ChatGPT Library at `/Project JRPG/Caelen V2/caelen_v2_down.png`. This repository change stages the implementation contract **without replacing the existing runtime**.

**Not yet final:** The more recently approved visual design remains a 2172×724 concept illustration, not an authentic 160×48 transparent sprite atlas. Do not claim the earlier simplified native prototype reflects the refined approved artwork. Pixel-authoring and review are still required before a production image is added.

Frame slots, left to right: idle; left-forward; passing; right-forward; passing. At 140 ms per walking frame, looping the four walk frames takes 560 ms. Preserve foot baseline, RGBA transparency, nearest-neighbor sampling, and player collision logic.

Proposed output when ready: `assets/atlases/characters/caelen_v2_down.png`; leave `caelen.png` and all active animation manifests intact until all directions are tested.
