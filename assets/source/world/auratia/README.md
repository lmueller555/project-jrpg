# Auratia classroom map source

`wall_map_generated.png` is the original imagegen adaptation of the approved
Auratia polar world map into a small, front-facing classroom prop. The old
school map sprite provided the framing and furniture palette reference.

The adaptation deliberately removes text and simplifies terrain into colored
shapes so the four continents, Rillan archipelago and two icy polar areas can
read at the school's existing 42×40 native sprite size. The generated source
is retained unchanged; `tools/build_auratia_world_map.py` exports its native
sprite with nearest-neighbor sampling and binary alpha.

The approved detailed map is retained unchanged as
`assets/world/auratia/world_map.png`, originally generated as
`exec-84160ef4-23a8-49eb-9aba-f8626924f576.png` and approved in chat. It is the
image the player inspects; the sprite is its classroom representation.
