# Mira bench work — pose source

`recipe.json` defines native sleeve/elbow/hand coordinates, shared head/shoulder leans, the planted station, tool pivots and all variable-duration timing. `parts/` contains the exact approved head, waist, pouch and legs sampled from the existing appearance references, plus each authored arm and tool layer.

This uses the established pose-and-parts workflow. No approved source sprite is overwritten and no existing walk template is changed. The new work poses and fitting are approved by the user. `tools/build_mira_bench.py` reconstructs the runtime sprites, source layers, fitting states and contact sheets.
