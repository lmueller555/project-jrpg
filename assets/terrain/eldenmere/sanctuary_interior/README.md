# Sanctuary interiors — review

- `interiors_review.gif` / `.png`: synchronized comparison at the same 2× scale.
- `bedroom/room_review.gif` / `.png`: 4× bedroom review.
- `hall/room_review.gif` / `.png`: 4× hall and reading nook review.
- `dining/room_review.gif` / `.png`: 4× communal kitchen/dining review.
- `connections_review.png`: proposed room and courtyard connections.

The floors are 10×10, 12×10 and 16×10 at 24px. Each native room has a 48px
north wall above its floor, a cutaway front and an unchanged 24×36 Caelan for
scale. The comparison shows three separate snapshots. It does not place three
Caelans in one continuous game map.

`interiors.json` records the three room manifests, eighteen new prop exports,
door links, review rectangles and clocks. Each room directory retains native
floor/wall/fixture/structure layers, planning masks, thirty-six lighting and
scene frames, a native still and `room.json`. Native furniture is referenced
from existing packs without rescaling. Draw structure and lighting, then objects
and actors by floor baseline; within a shared baseline, supporting furniture
precedes its tabletop props. The kettle steam layer follows the kettle. Reused
fire poses supply the hearth. Rugs and mounted pieces have no floor blocker.

Daylight, fire and steam repeat together after 10.8 seconds. The review GIFs
preserve native RGB values and integer enlargement. Identical held poses may
merge in bedroom/hall GIFs while retaining the full timeline.

Room portals include approach and spawn coordinates. The 32px hall exit aligns
with the sanctuary exterior doorway and links to courtyard foot (386,304).
Planning uses the established 24×12 actor probe; these masks are not engine
collision or map-transfer implementations.

Six approved bedroom inspect lines are retained in object metadata. Medicine,
food/oil and care bundles correspond to Halden, Elira and Venn. Other story
annotations explain the proposed visual meaning, not new canonical dialogue.
Detailed rationale and retained sources are under
`assets/source/terrain/eldenmere/sanctuary_interior/`.

Build: `tools/build_eldenmere_sanctuary_interior.py`.
Verify: `tools/test_eldenmere_sanctuary_interior.py`.
Status: review; all prior assets and narrative files remain unchanged.
