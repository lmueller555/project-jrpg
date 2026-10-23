# Mira workshop exterior source — review

`exterior_concept.png` and `props_concept.png` retain the original generated
sources. `recipe.json` records measured crops, native sampling sizes, landmark
material classification, scene registration, prop footprints and timing.
`parts/` contains the sampled native source pieces. Sampling uses nearest
neighbors, named existing materials and binary alpha at threshold 128.

The building occupies the reserved 5×3-tile ground rectangle at (576,360).
Its 168×168 drawing frame includes roof/smoke headroom and room for the sign
overhang; the ground rectangle is (12,96,120,72). The drawing origin is (564,264).
Three facade bands fit the centered 28px door and broad shuttered window to
character scale. The terracotta/ivory/oak ramps are reused from the approved
cottage variant, with existing stone, glass, iron and outline materials.

The six props are a vise-equipped workbench, mounted three-tool rack, cog sign,
timber rack, spare wooden cog/fittings box, and stool/watering-can group.
The sign uses nine 600ms poses over 5.4 seconds. Its top ring and fixed bracket
stay attached while the plaque shifts at most one native pixel. Smoke reuses
the approved cottage particles, translated to the new chimney. Existing grass
poses share the established 5.4-second breeze; the shared scene repeats in 10.8s.

A one-tile-deep dirt apron extends the existing approach using the approved
47-state dirt atlas and retiled local neighbors. Props stay outside the 48×48
conversation space and clear of the upper lane and woodland connection.
Caelan and Mira use unchanged approved front-idle sprites as scale references;
their placement does not establish MQ02 dialogue or event choreography.

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/project-jrpg/bin/python tools/build_eldenmere_workshop.py
PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/project-jrpg/bin/python tools/test_eldenmere_workshop.py
```

All earlier art, the approved sanctuary, town foundation and story are read-only.
The workshop interior, hand-cranked experiment, door interaction, transitions and
quest implementation remain future work. This exterior awaits user review.
