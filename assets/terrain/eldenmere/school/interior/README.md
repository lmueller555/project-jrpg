# Eldenmere schoolroom — approved

One bright classroom with a **16×12-tile floor** at native 24-pixel terrain scale.
The 432×384 canvas has floor rectangle [24,72,384,288], south threshold
[204,360,24,8] and a clear central aisle. The room compiler's safe arrival is
[216,342]. All 19 furnishing approaches are reachable by the game's 24×12 probe.

Three shared 64×40 desks provide six pupil places, each with a slate, chalk and
counting pieces drawn on its tabletop. Six approved up-facing chairs face the
writing board; the approved down-facing teacher chair faces the pupils. The
teacher's desk carries an open book, ink, quill and a slate. A repaired bookshelf,
reading bench, counting exercise, painted stream/mill/terraces map, child house
and dog drawings, small coats, paper lantern practice and a modest lit lantern
make the room a cared-for village learning space.

`structure.png` contains only the approved cottage floor/walls, beams and windows.
Furnishings remain separate sprites and have explicit ground footprints for
collision and depth sorting. `room.json` is compatible with
`tools/build_building_interiors.py::compile_room`. The existing animated hearth
is reused; 36 transparent lighting phases at 300 ms provide a restrained window
light cycle and the approved warm floor glow. No character routines are placed
in this pack. Liam's mother is recorded as the future teacher.

Rebuild with `python tools/build_eldenmere_school_interior.py`. New prop source
layers and the assembly recipe are retained under
`assets/source/terrain/eldenmere/school/interior/`. Existing assets are unchanged.
