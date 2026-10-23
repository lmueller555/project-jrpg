# Eldenmere cottage furniture source — review

The first reusable set contains a single bed with a cream pillow and folded sage patchwork quilt, a worn plank table, and a south-facing wooden chair. Their orthographic top-down projection matches the approved cottage interior. Wood and linen reuse its exact material colors; the quilt adds three muted sage shades. Furniture stays fixed while the approved room daylight cycles.

`furniture_concept.png` is the generated source sheet, retained independently of its original workspace copy at `/workspace/generated_images/exec-e7940935-c1cb-4640-bdc6-b4e354f3eb31.png`. The approved interior room was supplied as a visual reference. No existing character, story, interior shell or outdoor artwork is modified.

`recipe.json` records source crop rectangles, nearest-neighbor native sample sizes, transparent frame registration, the ten-color export palette and illustrative placements. Magenta is removed with the same explicit chroma rule as the interior source pipeline (red >160, blue >120, and both > green+70); surviving samples map to the nearest named RGB color. Exported sprites use binary alpha. There is no smoothing or runtime resizing.

The bed's visible source sample is 32×60 inside a 48×72 frame, the table 48×38 inside 48×48, and the chair 20×38 inside 24×48. Frame padding is transparent. Frames align to the 24px terrain grid; 24×36 Caelan remains unchanged. `floor_rect` values describe suggested local floor occupancy for future placement, not implemented engine collision.

The furnished scene reuses the approved 288×288 expanded separate room, structure and all nine lighting overlays without rewriting them. Furniture is kept outside a 72px-wide central corridor from the south entry to the north door. The left bed and right table/chair are illustrative art-review placements, not a named household or final level. Draw order is structure, approved daylight, furniture, original Caelan. Existing projected light does not intersect the furniture.

Build with `PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/project-jrpg/bin/python tools/build_eldenmere_cottage_furniture.py`; check with the same interpreter and `tools/test_eldenmere_cottage_furniture.py`. The builder retains native parts both here and in the runtime pack and creates a lossless 4× looping scene plus a 6× component board. The loop retains the approved 5.4-second timing; GIF encoding may combine held frames.

These furniture designs await review. Additional facings, sitting/sleeping poses, interactive furniture, household layouts, engine collisions, cupboards, shelves and hearth animation are future milestones.
