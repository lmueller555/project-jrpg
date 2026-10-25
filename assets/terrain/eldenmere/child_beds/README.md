# Compact children's twin beds — approved

Three single-level 32×48 bed sprites provide sage, blue and plum quilts for the
new children's households. Their visible 24×42 frames register the approved
cottage bed's occupied pixels with nearest-neighbor sampling. The wooden frame,
pillow, folded quilt and footboard keep the existing village furniture style;
wood and linen use the unchanged approved colors. Quilt colors come from the
three mothers' approved dress palettes.

`beds.json` records full repository-relative images, source layers, the common
floor rectangle `[4,12,24,32]`, and sort baseline offset 44. These are ordinary
single-level twins. The original adult bed is not edited.

Suggested two-bed positions are `[96,96]` and `[132,96]`, with clear south-side
approaches `[112,154]` and `[148,154]`. A single-child home can use the first
position. All existing furnishing approaches and the new bed approaches were
checked reachable in the three furnished standard cottages using Caelan's
24×12 collision footprint and the existing adults' foot blockers.

Rebuild with `python tools/build_compact_child_beds.py`. `variants_enlarged.png`
shows all three quilts at 6× native scale. The runtime household compiler owns
actual placement and child assignment.
