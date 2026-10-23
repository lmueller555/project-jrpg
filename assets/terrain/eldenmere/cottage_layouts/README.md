# Furnished cottage interiors — approved

| Cottage | Exterior ground | Interior floor | Native room canvas |
| --- | --- | --- | --- |
| Compact | 3×3 tiles | 10×10 / 240×240px | 288×336px |
| Standard | 4×3 tiles | 13×10 / 312×240px | 360×336px |
| Wide | 5×3 tiles | 16×10 / 384×240px | 432×336px |

Wall projection, cutaway caps and void are outside the floor dimensions. All three use unchanged approved furnishing sprites and original 24×36 Caelan. Furnishings are redistributed across the larger floors; their native sizes and counts are preserved. Compact combines sleeping/living and a short cooking corner; standard separates sleeping, dining and kitchen areas through placement; wide adds a cutaway sleeping/storage divider and three-seat dining group. No named household is assigned.

Review exports:

- `layouts_review.gif`: synchronized 10.8-second comparison, matching exteriors above interiors, all at 3× pixel scale, 3336×1608.
- `layouts_review.png`: matching still.
- `<size>/room_review.gif` and `.png`: each interior enlarged 4×.
- `<size>/scene_frames/`: 36 native frames at 300ms each.
- `<size>/room.json`: source sprites, placements, foot rectangles, approach points, door/chimney alignment and timing.
- `<size>/floor.png`, `walls.png`, `fixtures.png`, `partition.png`, `structure.png`: reusable native layers.
- `<size>/blocking.png`, `navigable_centres.png`: planning masks for a 24×12 floor probe, not engine collision.
- `<size>/daylight_mask.png`, `floor_glow_mask.png`: fixed local lighting masks; the latter's 128 value marks half-strength color mixing.

Entrance centers preserve each exterior door's relative position within one native pixel. Hearth chimney centers follow the exterior flues within half a native pixel. The entry route reaches every furnishing approach and Caelan's foot anchor with a conservative 24×12 standing footprint. The wide partition is now 12×144px, consumes existing floor area and leaves a 96px open southern passage. Furniture uses the source foot rectangles; visual projections can overlap when chairs tuck beneath a table, using floor-baseline draw order.

Fire, ember and local glow animations retain the approved 1.2-second clock; daylight retains 5.4 seconds. The combined loop is 10.8 seconds. Exteriors in the comparison are static closed states. This is a layout/scale review, not final household geography or a runnable game. No previous art files or story documents are changed.

Rebuild with `tools/build_eldenmere_cottage_layouts.py`; verify with `tools/test_eldenmere_cottage_layouts.py` in the documented Pillow environment. Source settings live under `assets/source/terrain/eldenmere/cottage_layouts/`. The three layouts are approved for main.
