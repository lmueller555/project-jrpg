# Wide western bridge and connected fence modules

The new bridge has a **72-pixel clear roadway**, equal to three 24px tiles
north–south. It still spans 288px east–west and retains two broken ends with
a fully transparent 74px central gap. The original bridge PNG is unchanged.

The source bridge was rebuilt with image generation to add rows of cobbles.
The final generation is uniformly reduced to 232×116. Its two isolated
abutments are cropped at the transparent center and padded apart on a
288×144 native canvas. This establishes the three-tile road depth while
preserving stone proportions and the riverbank-to-riverbank span. No runtime
stone pixels are painted or stretched nonuniformly by the exporter.

Native bridge metadata:

- Clear deck: rows 34 through 105, with exclusive bottom 106; 72px total.
- Deck sample columns: 56 and 232, away from the broken ends.
- Foot anchor: `[144, 94]`, deliberately inside the canvas.
- Deck center is 24px above the world anchor, matching road tile Y29 and
  bridge anchor tile Y30.
- Fully transparent central columns: 107 through 180, exclusive right 181.

`native_width_review.png` contains a review-only three-tile ruler. The live
bridge asset contains no annotations. The source recipe and runtime manifest
both retain measured deck bounds for renderer and collision checks.

The additional `fence_ns` module has two endposts joined by north–south rails,
within an 18×48 canvas. Its `[9,24]` center anchor lets an optional `[8,44]`
solid rectangle describe the vertical run directly. A `sort_offset` of 24
can align depth ordering with its southern end. `fence_corner` is a separate
36×36 corner sprite with bottom-center `[18,36]` anchor.

The unaltered generations, reference paths and exact bridge prompts are in
`prompts.json`; the fence prompt is in `fence_prompt.txt`. SHA-256 hashes and
all crop/scale/placement operations are recorded in `recipe.json`.

```sh
python tools/build_overworld_composition_art.py
python tools/build_overworld_composition_art.py --check
```

Export operations are limited to cropping, uniform nearest-neighbor scaling,
transparent padding, palette reduction and alpha cleanup. Only the separate
review image adds labels and a ruler.
