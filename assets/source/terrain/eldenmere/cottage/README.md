# Retained cottage source

`materials_concept.png` is the original generated cottage concept, guided by the approved mill close-up. The original generated file is retained at `/workspace/generated_images/exec-23ee3459-79bf-42cb-92ab-4e13a34b042a.png` in the creation workspace. This committed copy makes rebuilding independent of that workspace path.

`recipe.json` records its exact crop, native size, ground registration, component extraction order, door leaf, smoke origin, timings, palette additions and review placement. The builder samples nearest-neighbor, removes the flat magenta backdrop with an explicit RGB rule, and quantizes every opaque pixel to named ramps. It adds no antialiasing. The inherited approved mill palette is read only; cream plaster, warm lamplight and pale smoke have separate named additions.

`parts/building_native.png` retains the complete sampled appearance. The other retained component crops partition it exactly: earlier parts are removed before later crops, preventing duplicate pixels where windows/flowers overlap. Their registered composite reconstructs the complete native reference. Exported clean roof/wall inserts sample the same native materials; lit windows replace only glass colors. Their sample coordinates and assembly are recorded in `tools/build_eldenmere_cottage.py`.

The tool exports fixed structure, five hinged door poses, eighteen smoke and lantern phases, the components board, native scene frames and lossless nearest-neighbor looping reviews. These animations are explicit separate layers rather than a deformation of the entire building. All outputs are reproducible with the retained source and Pillow dependency from `tools/requirements-assets.txt`.

This is the first draft base cottage. Wider/compact variants, triggered gameplay entry, interiors and resident-specific identities remain future work pending appearance approval.
