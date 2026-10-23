# Elira's compact cottage — approved

The opening quest's bridge cottage uses the approved 10×10 floor template. This approved pack adds an unlit portable memorial lantern, a small fixed two-step stool and two shelf states. Halden's standard and the Venn family's wide interiors are proposed follow-on work and are not built here.

`props_concept.png` is the retained image-generated source. `recipe.json` records the exact transparent source crops, nearest-neighbor sample sizes and material palette; the builder makes sampled alpha binary at a threshold of 128. `parts/` retains native exported props. The lantern is 12×24 with a 10×20 painted silhouette; the stool is 24×24. Exporting does not rescale previous artwork.

The 48×40 shelf frames composite the complete approved 48×24 shelf at [0,16]. Books, pottery, brackets and wood remain identical in both states. The lantern sits in its open middle bay. The shelf mounts beside the rear window, clear of the hearth. The stool stands below, with a reachable approach at [154,118]. Its ground footprint is only a planning blocker; it is not a climb mechanic.

Rebuild from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/project-jrpg/bin/python tools/build_elira_interior.py
PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/project-jrpg/bin/python tools/test_elira_interior.py
```

The review shows the two discrete quest states simultaneously. Existing hearth and daylight animations retain their 1.2/5.4-second clocks and a combined 10.8-second loop. The stored lantern is unlit and does not flicker. No retrieval, reaching, carrying or climbing character animation is claimed. Engine interaction, saving quest state, collision and room transitions remain future work. No new Elira character design or narrative text is introduced.
