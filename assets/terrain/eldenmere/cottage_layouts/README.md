# Furnished cottage interiors — review

| Cottage | Exterior ground | Interior floor | Native room canvas |
| --- | --- | --- | --- |
| Compact | 3×3 tiles | 6×6 / 144×144px | 192×240px |
| Standard | 4×3 tiles | 8×6 / 192×144px | 240×240px |
| Wide | 5×3 tiles | 10×6 / 240×144px | 288×240px |

Wall projection, cutaway caps and void are outside the floor dimensions. All three use unchanged approved furnishing sprites and original 24×36 Caelan. Compact combines sleeping/living and a short cooking corner; standard separates sleeping, dining and kitchen areas through placement; wide adds a cutaway sleeping/storage divider and three-seat dining group. No named household is assigned.

Review exports:

- `layouts_review.gif`: synchronized 10.8-second comparison, matching exteriors above interiors, all at 3× pixel scale, 2256×1320.
- `layouts_review.png`: matching still.
- `<size>/room_review.gif` and `.png`: each interior enlarged 4×.
- `<size>/scene_frames/`: 36 native frames at 300ms each.
- `<size>/room.json`: source sprites, placements, foot rectangles, approach points, door/chimney alignment and timing.
- `<size>/floor.png`, `walls.png`, `fixtures.png`, `partition.png`, `structure.png`: reusable native layers.
- `<size>/blocking.png`, `navigable_centres.png`: planning masks for a 24×12 floor probe, not engine collision.
- `<size>/daylight_mask.png`, `floor_glow_mask.png`: fixed local lighting masks; the latter's 128 value marks half-strength color mixing.

Entrance centers preserve each exterior door's relative position within one native pixel. Hearth chimney centers match the exterior flues exactly. The entry route reaches every furnishing approach and Caelan's foot anchor with a conservative 24×12 standing footprint. The wide partition consumes existing floor area and leaves an open southern passage. Furniture uses the source foot rectangles; visual projections can overlap when chairs tuck beneath a table, using floor-baseline draw order.

Fire, ember and local glow animations retain the approved 1.2-second clock; daylight retains 5.4 seconds. The combined loop is 10.8 seconds. Exteriors in the comparison are static closed states. This is a layout/scale review, not final household geography or a runnable game. No previous art files or story documents are changed.

Rebuild with `tools/build_eldenmere_cottage_layouts.py`; verify with `tools/test_eldenmere_cottage_layouts.py` in the documented Pillow environment. Source settings live under `assets/source/terrain/eldenmere/cottage_layouts/`. Layouts await approval.
