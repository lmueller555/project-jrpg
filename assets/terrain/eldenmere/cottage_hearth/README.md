# Eldenmere animated cottage hearth — review

A reusable 48×72 stone hearth with four fire poses, subtly changing embers and soft local firelight. The stonework, logs and chimney stay fixed. Stone and wood reuse the approved interior colors; the fire adds a restrained orange/amber ramp. No indoor smoke is drawn.

- `frames/`: four full RGBA hearth frames, 300ms each, 1.2-second loop.
- `parts/`: native chimney, firebox and four 14×14 flame samples.
- `structure.png`: static body with coal marker pixels; not an extinguished state.
- `sprite_sheet.png`: 192×72 atlas, four 48×72 cells.
- `masks/`: flame union, ember pixels, warm stone rim and local floor-light intensity labels.
- `hearth.json`: sizes, frame timing, source recipe, palette and mask references.
- `lighting/`: binary-alpha room-sized floor overlays preserving the plank colors and texture.
- `scene_frames/`: 36 native 288×288 scene frames combining fire and approved daylight.

Review files:

- `room_review.gif`: 4× enlarged looping room, 1152×1152, 10.8 seconds.
- `room_review.png`: matching still.
- `hearth_review.gif`: 8× hearth close-up, 384×576, 1.2 seconds.
- `components_review.png`: all four hearth poses at 6×.

The hearth occupies the northwest wall beside the left window. Its broader firebox stays below the window; the nearby bed and all approved furnishings remain clear and unchanged. Warm light reaches only the adjacent stone and a small floor patch. The central 72px path stays open. The room retains the existing 5.4-second daylight cycle; the full scene repeats after two daylight cycles and nine fire cycles.

All sprites and overlays use binary alpha. The floor mask's 128 value means half-strength color mixing, not partial runtime alpha. The scene remains an illustrative separate interior art review; collision and interaction are not implemented. Rebuild with `tools/build_eldenmere_cottage_hearth.py`; verify with `tools/test_eldenmere_cottage_hearth.py` in the documented Pillow environment. Source and recipe live under `assets/source/terrain/eldenmere/cottage_hearth/`. This design and animation await approval.
