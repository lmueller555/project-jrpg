# Eldenmere — irrigation gate source

Status: approved following user review.

`materials_concept.png` retains the generated companion reference for open, closed, jammed and partly raised sluice states. The existing terrace close-up supplied visual material and scale guidance. The gate is a small manually lifted wooden board with two posts, one beam, stone footings, iron bands and a locking pin; it has no powered mechanism.

`recipe.json` records source crops, exact material ramps, native ground/sprite dimensions, six lift poses, animation timing, placement, review framing and scene sequence. The source wood and stone crops are sampled with nearest-neighbor scaling into `parts/post.png`, `panel.png`, `beam.png` and `stone.png`, using the named palette. `parts/fixed_structure.png` retains the stationary posts, beam and footings separately from the sliding board, handle and locking pin.

The native 24×36 frames project twelve pixels north of their 24×24 channel footprint. The board's open lift is eleven pixels; its jammed pose has a three-pixel skew and displaced pin. Straightening and lift poses are assembled from the same retained appearance pieces so geometry and materials stay consistent across states. The fixed structure composites last to keep the board behind its guides. Water uses the approved irrigation colors and six-phase clock.

The review reads the earlier terrace scene without rewriting it. It places the gate on an upper-level north-to-south straight channel and updates only the controlled downstream branch. Dry and trickle compatibility atlases retain the existing channel geometry, and the dry spillway restores exposed stone where its falling water is absent. Basins retain small still pools. A two-tick delay per channel cell stages the fill/drain front; these are authored art responses, not fluid simulation.

The source recipe's timeline cycles through jammed, repair, opening, open, closing, closed and jamming for review. All timed segments share the six-phase water clock. Captions are outside the native world image. The scene retains the prior northern terrace boundary unchanged, as the user requested; the newly placed gate has no elevation transition, and its downstream route only descends at the southern spillway.

Build with `python tools/build_eldenmere_gate.py`. Tests cover native palette/hard alpha, fixed structural pixels, all transition endpoints, open/closed/jammed output widths, unchanged open-channel output colors, localized idle water motion, controlled routing/elevation, delayed state signals, exact scene reconstruction, unchanged pixels outside the affected area, and full/close-up/state GIF pixels and timing. Source approval status survives rebuilds.
