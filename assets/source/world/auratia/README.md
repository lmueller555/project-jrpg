# Auratia classroom map source

`wall_map_generated.png` is the retained imagegen adaptation of the approved
2026-11-25 southern-Merovar world map into a small, front-facing classroom
prop. The previous source provided its wooden frame and furniture palette;
the approved detailed map supplied the revised geography.

The adaptation deliberately removes text and simplifies terrain into colored
shapes so the four continents, Rillan archipelago and two icy polar areas can
read at the school's existing 42×40 native sprite size. The generated source
is pinned by `approval.json`; `tools/build_auratia_world_map.py` exports its native
sprite with nearest-neighbor sampling and binary alpha.

The approved detailed map is retained unchanged as
`assets/world/auratia/world_map.png`, originally generated as
`exec-5c97cbf9-8cbd-4ef8-b55b-2740b6581125.png` and approved in chat. It is the
image the player inspects; its bytes are preserved exactly. The classroom
adaptation was generated as `exec-40ea2af5-0c36-4d94-8cb7-d05989c9661a.png`.
Its simplified geography includes elongated western Merovar, an open southern
approach to the northern kingdom, a central east–west river and two southern
north–south rivers. No miniature labels are attempted.

`approval.json` owns revision identifiers, approved original filenames, source
hashes and the geography binding between the detailed map and derived prop.
The exporter reads this record rather than embedding a historical filename.
Update the record deliberately when a subsequent map is approved; unexpected
artwork or prop-source changes are rejected before exports change. The
generated runtime manifest is `assets/world/auratia/map.json`.
