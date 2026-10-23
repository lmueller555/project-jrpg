# Sanctuary exterior — native source and appearance review

The approved exterior proposal is a modest village sanctuary: cream plaster, brown timber, blue-gray slate, fieldstone foundation, two front-left windows and one front-right window, paired timber doors slightly right of center, shallow canopy, left roof belfry with bronze bell and right kitchen chimney. Its ground footprint is 8×5 tiles. This first appearance export is static, with doors closed, bell still, lantern unlit and no chimney smoke.

`exterior_concept.png` is the retained image-generated source. `recipe.json` records the exact roof/belfry and facade/foundation sampling bands, native frame/ground rectangles, material landmarks, hard-alpha threshold and town registration. Nearest-neighbor sampling and named material mapping produce hard, unfiltered native pixels. Separate bands preserve a 32px doorway and character-scale facade while fitting the roof/belfry silhouette. Their small source overlap retains the eave/canopy join.

The palette reuses the approved cottage materials, plus the approved storage outline and a small muted bronze ramp for the bell. Roof/belfry/chimney and facade/foundation bands are retained under `parts/`; `exterior_native.png` is their assembled 216×216 transparent frame. The ground rectangle is [12,84,192,120]. Roof projection is drawing overhang, not an enlargement of the ground footprint.

The native door opening is recorded at [118,156,32,42]. Registering the ground at [264,168] gives drawing origin [252,84] and door center x=386. Caelan's front-facing foot anchor [386,304] aligns with that center on the existing courtyard approach. The original 24×12 probe reaches this point without changing the approved navigation masks.

The builder reconstructs the existing town's first native frame from its approved layers and read-only composition helpers, replaces only the sanctuary instance, and writes review exports in the new sanctuary directory. It does not modify the approved foundation, its images, old source artwork or narrative. Mira's workshop remains a placeholder. There is one Caelan at the commons in the full-town still and one at the sanctuary entrance in the separate close-up; these are alternative snapshots.

```sh
PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/project-jrpg/bin/python tools/build_eldenmere_sanctuary.py
PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/project-jrpg/bin/python tools/test_eldenmere_sanctuary.py
```

The exterior appearance is approved. The subsequently approved `sanctuary_charm` pack supplies smoke, lantern movement, a separate bell cue and garden dressing while preserving these original static images. Opening/closing doors and sanctuary interiors remain future work. No new religious emblem, interior assignment, dialogue, engine collision or room transition is introduced. Original review images are retained as the appearance record.
