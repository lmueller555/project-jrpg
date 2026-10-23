# Eldenmere — terrace materials and assembly source

Status: design and artwork approved following user review.

`materials_concept.png` is the retained generated companion reference for fieldstone walls, a corner, four broad stair treads and a spillway. It uses the approved irrigation close-up for visual style guidance. The original generated image is also retained in the execution workspace. `recipe.json` records source crops, native sizes, named stone colors, water glyph thresholds, phase timing, scene framing and approval state.

## Approved design specification

- Old, practical, maintained fieldstone; irregular loosely staggered courses, worn corners, quiet mortar, restrained cream highlights and sparse moss.
- One 24-pixel wall face including coping, assembled on the established 24×24 terrain grid.
- Three interchangeable straight textures, inside/outside corners, exposed ends, short shaded side faces and back coping pieces.
- One south-facing 48×48 stair prefab with four broad treads, worn centers, low cheeks and dirt landings.
- A stone-lined eight-pixel channel mouth, narrow fall, receiving basin and lower channel connection.
- Six phases at 200 ms synchronize the spillway with the existing stream and irrigation. Only water, impact flecks and ripples animate; structures and water silhouettes remain fixed.
- A single raised grassy terrace beside the irrigation, characters on both levels, and direct enlarged looping GitHub previews for visual review.

These decisions concern the art pack, not canonical Eldenmere geography, season or a finalized village map. Gate, bridge, mill, side-facing stairs and additional wall heights remain later work.

## Retained native source parts

The builder samples the reference with nearest-neighbor scaling and maps colors to exact named ramps. `parts/wall_material.png` is a 48×24 two-tile stone sample; `stairs_material.png` is a 48×48 tread/cheek sample. `fall_mask.png` and `ripple_mask.png` retain binary source highlight shapes. `spillway_structure.png` and `spillway_water_mask.png` separate all fixed masonry from the animated water region.

Assembly extracts three 24-pixel wall windows, standardizes the outer boundary profiles and coping, and constructs oriented corner/end/side pieces. Stair quarters remain exact crops of the complete assembled staircase. The spillway's fixed mask carries phase-offset falling highlights, source ripple pixels, small splash accents and a spreading ripple, then composites fixed structure last. No palette interpolation or partial alpha enters the native exports.

The review preserves the approved irrigation scene's upper sixteen rows, adds grass below it, routes native channel modules through the upper terrace and spillway into the lower network, and places unchanged native sprites on both levels. Dirt landings use the existing 47-blob lookup. All placements and native frames are exported for reconstruction.

Build with `python tools/build_eldenmere_terraces.py`. `python tools/test_eldenmere_terraces.py` checks native dimensions/palette, straight-wall boundary compatibility, fixed structures, water-only motion, current translation, port geometry and bank compatibility, upper-to-lower flow reachability, character clearance, exact scene reconstruction and enlarged GIF pixels/timing. Source recipe approval status survives rebuilds.
