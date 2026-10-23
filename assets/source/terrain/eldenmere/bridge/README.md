# Eldenmere — bridge source and design

Status: draft artwork for visual review.

`materials_concept.png` retains the generated companion reference for an east–west timber bridge, reusable plank material, rails/post/lantern details and an equal-bank stream crossing. The approved gate close-up supplied palette and style guidance. `recipe.json` records crops, native dimensions, module assembly, lantern poses, placement, elevations, source scene phases and review framing.

## Design decisions

- A flat east–west bridge with a 48-pixel deck width, built on the established 24×24 terrain grid.
- Four 24-pixel columns in the first assembly: bank-supported west end, two interchangeable middle textures over a 48-pixel water span, bank-supported east end.
- Weathered but maintained timber, quiet grain, transverse planks, low rails, iron straps and stone abutments using the approved palette without new colors.
- Flush stone thresholds meet equal-height approaches. Both banks and the deck share elevation 24; water surface elevation is 16. The bridge introduces no slope, stair or uphill water route.
- Small hanging festival lanterns at the ends, with one-pixel sway; restrained downstream wakes beside short timber support feet.
- Stationary decking, posts, rails and stone. A separate foreground rail allows correct character occlusion.
- Native 24×36 Caelan on the bridge and enlarged direct GitHub previews for review.

For future scene work, establish ground/deck/water elevations before routing water or placing crossings. Water should remain below the deck and descend only at deliberate drops. The earlier terrace example is retained without alteration, following the user's instruction.

## Source and assembly

`parts/planks.png`, `rail.png`, `post.png`, `stone.png` and `paper.png` are nearest-neighbor material samples mapped to the exact approved named ramps. Planks retain the reference's grain and restrained worn patches; mirrored middle variants reduce repetition. Shared boundary profiles make deck and rail joins compatible. Flat stone thresholds and short abutment faces are separate from the wooden walking surface.

The builder creates 24×72 module layers, places rear and near rails on separate layers, and assembles complete 96×72 sprites. Lanterns retain fixed brackets and small phase-offset paper bodies. Water shadows and wakes are separate overlays for clipping against actual water. Structural layers are written once; native frame animation changes only lantern pixels. The six-phase 200 ms clock matches the existing stream.

The scene reads native gate frames 43–48, when the gate and all downstream branches are open, without rewriting them. It extends the grass canvas by two columns, adds a dirt approach on the east, restores the two ground cells previously containing Caelan and draws his unchanged right-facing idle over the bridge. Layer order places the near railing after the character. All pixels outside the new bridge, Caelan's former cells and the new right-hand canvas match those source frames.

Build with `python tools/build_eldenmere_bridge.py`. Tests cover native dimensions/palette/hard alpha, layered sheet reconstruction, compatible joins and multiple span lengths, lantern/water-only motion, correct foreground order, actual dry-bank/water cells and equal elevations, character clearance, exact scene reconstruction, localized changes and pixel-exact enlarged GIF timing. Recipe approval status survives rebuilds.
