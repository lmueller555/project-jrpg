# Tomas — work and carry pack

Review assets for preparation, delivery, storage, crank-model tinkering and
courtyard glances. `animations.json` is loaded by the existing `RoutineNPC`
system; the schedule is `assets/maps/eldenmere/routines/tomas.json`.

Body artwork remains the approved Tomas design. Action frames are padded
64×48 PNGs, using `[32,36]` scene anchors and `[20,6]` body offsets. The bundle
has one owner across table, hands and storage. The fixed model base does not
move while the wheel, peg and crank rotate. Four carry walks retain the shared
140 ms timing. No quest or follower behavior is activated.

Build with `python tools/build_tomas_routines.py`. See
`docs/reviews/tomas_routines/README.md` for looping in-scene previews and the
continuous runtime video. This pack is awaiting user review.
