# Elden Vale Sanctuary overworld art

`generated_miniature.png` is the unchanged image-generation source, guided by
the sanctuary concept reviewed in chat and the existing Eldenmere miniature.
The source preserves the limestone hall, blue-grey slate roof, circular oculus,
small bellcote, and low three-arch cloister. It adds no cave or detailed reserve.

`recipe.json` records source and reference hashes, crop rectangles, alpha cutoff,
uniform nearest-neighbor scaling and canvas registration. The reviewed concept
path records authoring provenance only; rebuilding needs only the retained
generated source and recipe, and does not call image generation.

Run `python tools/build_overworld_sanctuary_art.py`, or pass `--check` to verify.
The 96×80 miniature is smaller than Eldenmere's 144×120 sprite. It has binary
alpha and an irregular silhouette, and supplies no collision or travel behavior.
The approach uses the ordinary dirt path; the former standalone steps are no
longer exported or placed because the overworld has no matching height change.
