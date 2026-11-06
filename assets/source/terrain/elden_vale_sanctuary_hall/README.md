# Elden Vale Sanctuary hall

`generated_hall.png` is the retained actor-free image-generation source for the
regional sanctuary's stone hall. The exterior approved in chat provided its
limestone, timber, daylight and nature motifs. This room is separate from
Serene's home: it contains a remembrance table, reading benches, a records
table and a closed book cabinet, with no domestic bedroom or kitchen.

`recipe.json` records the source hash, uniform native scale, full-foot navigation
rectangles, furniture footprints, exact depth silhouettes and inspection
approaches. `tools/build_sanctuary_reserve_hall.py` exports the native 576×384
plate, six matching scenery overlays, collision and runtime metadata.
The overlays cover the benches, records table, cabinet edge and southern plants
at their individual ground anchors. Gaps between furniture legs and foliage
remain transparent. The central aisle and southern doorway stay clear.

Rebuild with `python tools/build_sanctuary_reserve_hall.py`; use `--check` to
verify every product against the retained source. The original generated
art remains unchanged. No baked people, quest flags or hidden-history reveal
are part of this room.
