# Elden Vale aerial cinematic landscape sources

These authored cinematic plates depict the existing Elden Vale region. The
source geometry is `assets/maps/overworld/elden_vale/region.json`; the complete
unlabelled layout reference was rendered from its atlas, actual roads, walls,
village, farms, gates and broken crossing. It is not a generic landscape.

`region_generated.png` follows the north-up reference. Its exported bounds are
`[-177, -112, 354, 236]` tiles on a 1536×1024 canvas. Eight independently checked
painted landmark centers are within 1.73 tiles of their runtime counterparts.
Both boundary rivers remain continuous; the only river crossing is the broken
western bridge. `region_banks_generated.png` supplies four bounded water crops
that remove short painted wall stubs over river water. Every region pixel
outside those rectangles remains byte-identical to the first approved source.

`gate_overhead_generated.png` is a true orthographic view: roof and capstone
tops rather than standing facades. Its bounds are `[-2, 76, 60, 40]` tiles;
the west/east post caps are at native `(718,514)` and `(819,513)`.
The west gatehouse is the existing cinematic gatehouse. The separate small
east lean-to corresponds to the actual inside-wall duty shelter.

`gate_oblique_generated.png` supplies the lower, steep oblique view of the same
checkpoint. Registration uses post bases `(720,455)` and `(875,455)` for world
tiles `(26,96)` and `(30,96)`. `gate_open_generated.png` supplies only a bounded
open-road crop to remove a thin baked bar; the renderer owns the gate leaf.

`gate_high_oblique_generated.png` is an earlier candidate retained for source
provenance. It is not exported as the orthographic overhead plate. Original
generations, the exact prompts and reference diagrams are retained. No people,
birds, caravan, guards or user interface are painted into the exported plates.

The exporter only copies bounded authored source crops and exports PNGs. It
does not repaint geography, stretch architecture or alter original sources.

```sh
python tools/build_regent_aerial_landscape.py
python tools/build_regent_aerial_landscape.py --check
```

Native canvas coordinates, geographic bounds, crop rectangles and SHA-256
fingerprints are recorded in the exported manifest and provenance.

## Foreground canopy

`foreground_canopy_generated.png` is an independently authored transparent
close oak bough matching the existing gate's sunlit foreground foliage. It
sweeps close to the camera during the last descent. The renderer changes
registered background plates only while the opaque painted leaves cover the
whole native viewport, rather than dissolving different terrain shapes.

Its exporter snaps source alpha at 128 and nearest-resizes to 960×640 without
painting or filling holes. The manifest's `foreground_canopy.coverage_rect`
is the largest rectangle of actual fully opaque alpha, measured as `[x,y,w,h]`.
This guarantees full coverage at the declared near scale; a silhouette bounding
box alone would not prove occlusion. Outer leaves remain irregular and the
perimeter remains transparent. The original three landscape PNGs are unchanged.
