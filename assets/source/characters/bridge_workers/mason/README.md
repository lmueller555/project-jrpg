# Authored bridge mason animation sources

The four original image generations and their exact prompts are retained here.
The mason preserves the approved `male_01` brown hair, green shirt, tan/brown
trousers and boots. The black-haired loader sheet is a pose reference only.

`tools/build_bridge_mason.py` registers complete authored bodies on a 40×44
transparent canvas with foot anchor `[20,38]`. It never draws or rotates limbs,
warps a torso, or recolors isolated parts. Normal town idles and walks remain
read-only approved assets.

Work and cargo frames include proper side views; all four stone/cup directions
have loaded walks and neutral blocked holds. The full side-facing seated source
is reflected as one complete body to face the bench. One fixed physical scale
throughout sitting, sipping and standing preserves the shorter seated body and
the original head and torso proportions. It does not stretch seated frames to
standing height.

The stone, cup and tool are separate controller-owned props. Frame metadata
records painted hand contacts, the seated contact underside and the actual
painted mouth. The raised cup's opaque rim reaches that mouth pixel. The
right-facing cargo body also supplies a compatible right cup walk because the
generated cup sheet omitted that final row; this is whole-body pose reuse.

Run `python tools/build_bridge_mason.py --check` for byte verification.
`native_review.png` composites the exported bodies and actual live prop images.
