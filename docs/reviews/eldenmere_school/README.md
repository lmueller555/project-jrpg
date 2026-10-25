# Eldenmere school — awaiting review

- [School exterior and shaded yard](exterior.gif)
- [Whole furnished classroom](interior.gif)
- [Actual doorway entry, exploration and exit](door_walkthrough.gif)
- [School location on the town map](town_layout.png)
- Still views: [exterior](exterior.png) · [interior](interior.png)

Captured from the production `main.py` renderer and live game updates at normal
speed. The exterior loop shows a 5.4-second cycle of chimney smoke, lantern,
book-sign movement and the established foliage breeze. Caelan stands near the
entrance, keeping the proximity door open; the walk-through separately shows
all four door states and a real town → school → town round trip.

The classroom has a 16×12-tile floor, six pupil seats at three shared desks,
teacher's table and chair, writing board, village map, book shelf, children's
work, coat pegs, reading bench and festival corner. Daylight and the hearth
animate over a 10.8-second loop. The full-room review joins two native renderer
viewports at identical world positions and time, showing the whole interior
without changing its layout. The walk-through uses the normal gameplay camera.

The school is on lower ground northeast of the well, south of the workshop and
west of the stream. The yard and footpath connect to the well square. Liam's
mother is assigned as its teacher; teaching, pupil attendance and schedules are
a later stage. No teacher or children have been moved from existing routines.

Reproduce with `python tools/build_eldenmere_school.py`, then
`python tools/capture_eldenmere_school.py`. `captures.json` records scene and
door evidence, GIF timing, and scope. This branch is published for review and
has not been merged into main.
