# Source atlas seam audit (pending art repair)

Run `python -m tools.terrain.audit_grassland_seams` to compare a reproducible set of 32px sprite boundaries. This measures RGB discontinuities; it **does not** certify blob coverage or corner joins.

On a locally reproduced 256x256 atlas from the approved 1254x1254 source using the checked-in slicer, several adjacent source cells showed substantial edge differences, e.g. grass variants slots 0/1 averaged ~35 RGB intensity levels per channel; illustrated transitions 24/25 averaged ~48. These illustrative pairs are **not** a canonical-mask composition and are evidence that proximity in the atlas cannot serve as a valid mapping.

To complete the requested implementation, the image must be reauthored as a provably continuous 47-mask set, with each canonical mask's ground coverage and inside/outside corners verified in composed maps. Then the original 16-unit map can be rendered on the 32px presentation canvas. Do not wire current slot order into Eldenmere.
