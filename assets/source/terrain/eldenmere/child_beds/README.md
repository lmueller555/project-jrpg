# Compact twin-bed source

`tools/build_compact_child_beds.py` crops the approved adult bed's occupied
rectangle `[8,6,32,60]`, registers it to 24×42 with nearest-neighbor sampling,
and places it at `[4,3]` in the new 32×48 frame. The original sprite's SHA-256
is recorded in `recipe.json` and checked after the build.

Each family quilt retains three transparent layers: wood frame, pillow/linen,
and folded quilt. Their ordered composition reconstructs the matching runtime
image exactly. Recoloring affects only the approved quilt material ramp.
