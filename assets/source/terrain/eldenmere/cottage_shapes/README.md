# Cottage shape source — approved

The approved 4×3 cottage and four palettes are retained on main at `4c3a19700ff4c34f93809711a5b93b3a860a426d`. This pack builds 3×3 and 5×3 layouts directly from those native components. The original source and exports are read only.

`shape_concept.png` is a structural design study guided by the approved cottage; its original remains at `/workspace/generated_images/exec-68b6f197-1043-43dd-9818-c1772159417e.png` in the creation workspace. It illustrates compact/wider architecture. Native exports use the approved components and exact palette pixels, rather than resampling the study.

`recipe.json` records every source directory, crop, band removal/insertion, material repair, detail placement, animation offset, footprint and review placement:

- Compact: repair the source left window/flower region using sampled plaster/stone from the approved blank wall insert, then delete columns 24–47. Only the five-pixel tail west of that deleted bay needs the repair in the resulting facade. Retain the complete right window and move the approved flower crop beneath it. The door is left of center; the hanging lamp remains beside its original post.
- Wider: insert a 24-pixel bay at column 48 using the approved roof-repeat and blank-wall modules. Add an unscaled copy of the approved right window in the new bay. Preserve both original windows, the flower box and doorway.
- Both: translate the complete approved door, smoke and lantern layers by −24 or +24 pixels respectively. No detail is resized and no animation is regenerated. The roof/chimney, door and lamp all move consistently with their source bay.

Each palette is assembled from its own approved native parts, including protected flower/light/stone colors and existing roof shading aliases. The source recipe supplies exact registrations, so no color remapping or quantization is needed in this builder. Exported west/east spans, inserts and decorations reconstruct the fixed structure in metadata order. Five door poses, eighteen ambient phases and separate optional smoke remain available as individual layers.

Build with `PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/project-jrpg/bin/python tools/build_eldenmere_cottage_shapes.py` and verify with `tools/test_eldenmere_cottage_shapes.py` using the same interpreter. Both silhouettes and all four palette assemblies are approved alongside the existing base cottage.
