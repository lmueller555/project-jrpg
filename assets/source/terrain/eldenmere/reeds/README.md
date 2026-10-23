# Eldenmere bank reed source — review

`materials_concept.png` retains the generated tall/short reed source, guided by the approved watermill scene. Its original remains at `/workspace/generated_images/exec-f423537d-2391-48e0-96af-4981c4cb1d90.png` in the creation workspace. The committed source is sufficient to rebuild elsewhere.

The tall clump has three brown seedheads and narrow arching leaves; the shorter juvenile variation has green shoots without brown heads. `recipe.json` records exact source crops, native sample sizes/positions, hard-alpha coverage threshold, material ramps, fixed-root boundaries, bend bands, poses and scene placements. Tall source art samples to 20×36 inside a 24×48 frame; short art samples to 18×21 inside 24×24. Both have 24×24 ground anchors. The tall anchor starts at native row 24, allowing a 24-pixel north overhang.

The exporter removes magenta before sampling. BOX sampling on premultiplied RGBA retains thin source stalks that could fall between nearest-neighbor sample centers. Coverage below 48/255 is discarded; every retained pixel becomes fully opaque and receives the nearest named material color. Thus fractional coverage is an export decision only, never runtime transparency or blurred sprite edges. Green stalks/leaves use the approved six foliage shades. Warm source brown pixels above native row 26 use the existing four cottage-wood shades for seedheads; all lower pixels and the entire short variation use greens.

`parts/` retains native rest art, three disjoint horizontal bands and a fixed base for each plant. The upper band contains complete seedheads; a shallow bend propagates through lower stems/leaves with at most one pixel of eastward movement and no vertical displacement. Tall rows 44–47 and short rows 20–23 remain fixed. All stalks, leaves and heads stay connected, no pixels are clipped, and pose zero reproduces the sampled native source exactly. Nine 600 ms poses, including held gust/settling pauses, share the approved 5.4-second breeze.

Seven illustrative placements (four tall, three short) extend all 54 approved grass/flower scene frames. Their bases occupy dry grass, their complete animation masks cover grass only in every prior foliage phase, and their roots remain near visible water. All use the existing upper-bank elevation 24; known brook/mill-race water levels are retained in placement metadata. Upper-irrigation water geometry and elevation are inherited without assigning a new surface level. New plants overlap neither each other nor existing water, structures, paths or characters. No watercourse, masonry, gate or crossing is altered. This scene demonstrates art, not canonical village geography or gameplay collision.

Build: `PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/project-jrpg/bin/python tools/build_eldenmere_reeds.py`.

Test: use the same interpreter with `tools/test_eldenmere_reeds.py`.

The two designs and animations await review. Additional reed shapes and denser shoreline planting can follow after approval.
