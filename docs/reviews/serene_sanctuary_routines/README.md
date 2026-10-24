# Serene's sanctuary routines — review

Status: awaiting user review. These four previews isolate the recurring work
motions while retaining their real in-game rooms, furniture, depth sorting and
ambient animation.

- [Sorting provisions](provisions.gif) at the two care-supply tables in the
  sanctuary dining room.
- [Checking the preparation list](preparation_list.gif) at the dining-room counter.
- [Tending the hearth](hearth.gif) beside the dining-room fire.
- [Arranging hall linens](hall_linens.gif) at the sanctuary mending table.

Each GIF enlarges a native scene by 4× with nearest-neighbor scaling. Serene is
registered from the sanctuary schedule's review coordinates, selected through
the runtime `RoutineNPC` API, and passed through the normal `World` renderer,
including entity depth order. Every character pixel comes directly from
`assets/characters/serene/routines/animations.json` and its referenced PNG
frames; the capture script does not draw, mutate or substitute sprites.

Reproduce all four previews with:

```bash
python tools/capture_serene_routines.py
```

The capture reads its room, station and crop for every action from
`assets/maps/eldenmere/routines/serene.json`. It validates all four action keys,
declared timing, 48×48 frame size and every referenced PNG before writing
output. Missing or incomplete action assets stop the command with a concrete
error instead of producing a fallback animation.
