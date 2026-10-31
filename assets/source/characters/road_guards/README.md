# Elden Vale road guards

The retained image-generation sheet expands the original closed-visored guard
identity: silver plate, brass edges, navy tabard, leather strap, brown boots and
a rectangular shield on the physical left arm. Front, back and both profiles
are independently authored; the runtime never mirrors their asymmetric gear.
The portrait uses that same helmet and uniform instead of a civilian face.

`directions_generated.png` and `portrait_generated.png` are unchanged originals.
`prompts.json` retains the generation requests and appearance references.
`tools/build_road_guards.py` registers complete full-body cells on a transparent
40×44 canvas with foot anchor [20,38], using one uniform scale and nearest
sampling. It does not draw arms, warp torsos or change collision footprints.

The generated back-row gesture lifts the equipped arm incorrectly, so that
cell is excluded. Back-facing conversation uses the actual back idle/breath
poses; the other three views have a small right-hand acknowledgement. A greeting
plays only once, then settles to a slow idle rather than looping a hand wave.

`native_review.png` presents the actual exported poses at 4× for inspection.
The dedicated 72×72 portrait lives in the ordinary portrait catalogue.

```sh
python tools/build_road_guards.py
python tools/build_road_guards.py --check
```
