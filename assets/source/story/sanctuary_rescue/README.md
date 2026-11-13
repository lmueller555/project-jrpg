# Cave rescue body sources

Three retained image-generation source atlases supply independent, naturally
posed character drawings. `reference.png` is an enlarged identity reference
assembled from the current runtime worker, Lucan, Mira and Caelan sprites.
It is a reference only, not exported body artwork.

`actions_authored.png` has four columns and six rows: seated/pinned worker,
assisted worker rise, leftward supported worker steps, Lucan's empty-handed
brace/lift, Mira's kneeling work/treatment, and Caelan's helping gesture.
The worker faces left; the three helpers face right. No body parts or limb
lengths are procedurally warped to force contact with scene objects.

`worker_supported_authored.png` and `lucan_supported_authored.png` each have
four columns by four rows, directional supported walking front/back/left/right.
Lucan's bank is explicitly empty-handed and does not expose weapons or tools
while supporting the worker. The source drawings retain their anatomical hand
sides instead of obtaining opposite views by mirroring.

The builder selects each cell's largest hard-alpha component and reduces it
with nearest-neighbour sampling at one fixed scale per character/source bank.
The 40×40 transparent canvases provide padding for the seated leg and helping
hands. The common (20,34) draw anchor keeps the native body's ground baseline
consistent with ordinary (12,30) anchors on 24×36 travel canvases. Body size is
roughly 34 native pixels when standing; bent joints account for shorter poses.
`registration.json` records all cells, source bounds, scales and destinations.

The Sanctuary caretaker retains the existing gray-haired arrival identity. Its
`receive` pose reuses the existing leftward reach/recovery drawings from the
rope-unhook bank without a rope object; this is a standing assistance gesture,
not an invented kneeling pose.

The loose slab reuses limestone fallen-slab artwork at 36×24; the tiny pry tool
is cropped from Mira's existing mill action layer; the dressing is the existing
Sanctuary linen sprite. Their source hashes are retained in `art.json`.
Scene code owns placement, stone release, tool visibility and dressing deposit.
No imagery grants inventory, healing or quest progression by itself.

Run `python tools/build_sanctuary_rescue_art.py --check` to verify byte-for-byte
reproduction. New artwork remains marked `review` until user visual review.
Numerical checks do not substitute for inspection of the production scene.
