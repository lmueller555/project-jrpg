# Female NPC 01 — back walk

Status: draft for user review. The front walk and all directional idles remain approved.

Four 24×36 frames use the shared back stride at 140 ms per frame, looping in 560 ms with foot anchor `[12, 34]`. The head retains the centered low bun and no visible eyes. The head, neck, shoulders and upper bodice rise together by one pixel on passing frames 02/04. All motion offsets are baked into the frame pixels.

Dedicated blue-dress poses keep a fixed waist, a one-pixel lower-skirt sway on contacts, and a hem lift from row 28 to 27 on passing frames. Per-phase leg splits and boot-top boundaries keep the shared stride silhouettes while exposing bare calves and brown ankle boots beneath the skirt. Back views never introduce eye pixels.

- `frame_01.png`–`frame_04.png`: native transparent frames.
- `spritesheet.png`: 96×36 native playback strip.
- `animation.json`: status, timing, rectangles, phase, bob and posed layer paths.
- `walk_back_preview.gif`: 20× nearest-neighbor looping review on a light background.
- `frames_review.png`: all four frames enlarged 12×.
- `shared_motion_comparison.gif`: synchronized 12× Caelan/NPC comparison.
- `recipe.json`: approved idle/palette references, shared template and authored costume poses.

Rebuild from the repository root with `python tools/build_dress_walk.py --direction back`. Use `--direction all` to rebuild all base directions and `../walk_directions_review.gif`. New directions stay drafts until user approval; palette walk variants are later work.
