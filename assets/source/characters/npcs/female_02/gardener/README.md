# Gardener — retained pose source

`recipe.json` defines occupied arm joints, bucket grips, head/shoulder leans, carrying depth, native body/action registrations, bucket materials and action timing. `parts/` retains each newly articulated arm layer.

`tools/build_gardener.py` reconstructs all outputs from these instructions and the approved female_02 appearance and walk parts. It preserves head/eye colors, dress scale, boot pixels, walking leg phases and skirt motion. Some older walk metadata references unexported neckline layers; the builder samples their registered rectangles directly from the approved composites rather than changing those source packs.

The bucket and work poses are approved by the user. Original sprites and shared templates remain unchanged.
