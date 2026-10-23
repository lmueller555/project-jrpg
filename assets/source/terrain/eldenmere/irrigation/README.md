# Eldenmere — irrigation source and assembly

Status: draft artwork for user review.

`materials_concept.png` is the generated companion-art reference for a thin earth-lined straight, bend, junction and trickling outlet. The approved stream close-up supplied color/style guidance. Native exports reuse the exact approved material ramps and the stream's six-phase, 200 ms timing.

`recipe.json` records native width/scale, appearance crops, droplet extraction threshold, current speed/spacing, outlet poses, base terrain references and review framing. `parts/earth_strip.png` samples the source earth bank into named material colors; `parts/droplet_mask.png` retains the source's small droplet silhouette as binary alpha. Sampling and review scaling use nearest-neighbor without interpolated or partial-alpha pixels.

`shapes/` retains bank and water-mask pairs for cardinal masks 0–15, plus four stream-intake and four outlet orientations. The geometry is built on the 24-pixel grid with an eight-pixel channel and two-pixel earth edges. A shallow rim is baked into the stationary bank layer. The empty zero slot is transparent. Source earth texture is applied sparingly away from shared borders so static joins match exactly.

The builder assembles all 32 directed channel routes by choosing each connected port as the input and the remaining ports as outputs. Incoming current marks move toward the center, then move outward along each output. Their 12-pixel spacing and two-pixel phase step preserve motion across 24-pixel joins. Inlets open a narrow mouth through a straight stream bank. Outlets add a small moving thread, extracted droplet and receiving-puddle ripple; fixed bank art remains a separate retained layer. Ninety-degree orientation changes use exact native-pixel transposes.

The expanded review reads the approved stream scene and ground assets, extends its grass area and overlays a routed channel network. No existing asset or story document is rewritten. Two native character placements change only in this review scene. Its topology is schematic and establishes no canonical village geography.

Build with `python tools/build_eldenmere_irrigation.py`; check with `python tools/test_eldenmere_irrigation.py`. Tests verify 240 exported module frames, material/hard-alpha conformance, localized motion, every compatible directed structural join, actual two-pixel motion in all four straight directions, source-to-outlet reachability, exact native scene reconstruction, nearest-neighbor review GIF pixels and six-frame timing. Approval status comes from the source recipe and survives rebuilds.
