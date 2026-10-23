# Eldenmere cottage kitchen source — approved

The user selected a kitchen counter, washbasin and pantry storage. The static set contains a two-door wooden work counter with a cream cutting board, a ceramic basin of still water on a short wooden stand, and narrow open pantry shelves with jars, a plain basket and bread. No cloth ties, plumbing or additional animations are introduced.

`kitchen_concept.png` is the generated source, originally `/workspace/generated_images/exec-1589b14d-9a1e-4883-a86d-4fbfef526ebb.png`. The approved hearth room supplied the visual reference. The committed source is independent of that workspace path. The earlier writing-desk source generated before the user's selection is not part of this pack.

`recipe.json` records source crops, nearest-neighbor native sample sizes, transparent registration, palettes, suggested floor footprints and illustrative placements. Export frames are 48×48 for the counter, 24×36 for the basin and 24×48 for the pantry. Magenta removal uses red >160, blue >120 and both > green+70; remaining pixels map to the nearest allowed named material. In the counter's source-sample handle region, gray/blue source pixels use the iron ramp. All exported alpha is binary. Palette colors exactly reuse approved wood, outline, cream plaster, iron and glass/water-like blue colors. There is no smoothing or dithering.

The new room remains the 10×8-floor asset showroom, not an assigned cottage size. Counter and basin replace the cupboard's former review position below the right window; the cupboard moves beside the bed. The pantry stands below the wall shelf. Bed and dining table keep their positions. One approved up-facing chair remains below the dining table; the other three facing examples remain in their original pack. All approved sprite files, original review exports and story files remain unchanged.

The builder reads and assembles existing room, furniture, storage and hearth exports without rewriting them. It reuses all 36 hearth/daylight phase records and floor-glow overlays, preserving the 10.8-second joint loop. Kitchen props and basin water stay fixed. The 72px central route stays clear. These remain illustrative placements; engine collision and interaction are not implemented.

Build with `PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/project-jrpg/bin/python tools/build_eldenmere_cottage_kitchen.py`; verify with the same interpreter and `tools/test_eldenmere_cottage_kitchen.py`. Native source parts are retained both here and in the runtime pack. The 144×48 atlas uses three 48×48 padded cells. Room review is enlarged 4× and component views 8× using nearest-neighbor scaling.

Kitchen designs are approved. The separate `docs/art/COTTAGE_INTERIOR_PLAN.md` records a proposal for compact, standard and wide cottage interiors; it does not implement or approve those floor plans.
