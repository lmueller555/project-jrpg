# Female NPC 01 — left walk

Status: approved by the user in chat. The front walk and all directional idles remain approved.

Four 24×36 frames use the shared left stride at 140 ms per frame, looping in 560 ms with foot anchor `[12, 34]`. The head retains one blue iris and the approved profile bun. The head, neck, shoulders and upper bodice rise together by one pixel on passing frames 02/04. Profile arm masks exclude the shared character's neck pixels, and the approved neckline is restored above the arms before compositing the head. All motion offsets are baked into the frame pixels.

Dedicated blue-dress poses keep a fixed waist, a one-pixel lower-skirt sway on contacts, and a hem lift from row 28 to 27 on passing frames. Per-phase leg splits and boot-top boundaries keep the shared stride silhouettes while exposing bare calves and brown ankle boots beneath the skirt. Back views never introduce eye pixels.

- `frame_01.png`–`frame_04.png`: native transparent frames.
- `spritesheet.png`: 96×36 native playback strip.
- `animation.json`: status, timing, rectangles, phase, bob and posed layer paths.
- `walk_left_preview.gif`: 20× nearest-neighbor looping review on a light background.
- `frames_review.png`: all four frames enlarged 12×.
- `shared_motion_comparison.gif`: synchronized 12× Caelan/NPC comparison.
- `recipe.json`: approved idle/palette references, shared template and authored costume poses.

Rebuild from the repository root with `python tools/build_dress_walk.py --direction left`. Use `--direction all` to rebuild all base directions and `../walk_directions_review.gif`. All four blue base directions and all eight sage/plum palette walk cycles are approved.
