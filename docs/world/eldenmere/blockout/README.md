# Eldenmere overhead blockout 01 — approved

Approved geographic concept for a 64×56-tile village on the established 24px grid. This is a planning diagram with measured footprints, routes and relative elevations. It is not new terrain/sprite artwork, a decorated level or a collision-ready map. Existing approved assets remain unchanged. The subsequently approved terrain pass records the native-art fitting adjustments under `assets/maps/eldenmere/terrain_foundation/`.

## Review files

- `overhead_blockout.png`: 2304×1600 labeled geography, relative ground levels, paths, steps, crossings and water directions.
- `quest_routes.png`: the same plan with an orange first visit, a purple example loop, Tomas's dashed gray return and the dashed blue woodland connection.
- `overview_small.png`: half-size overview for quick inspection.
- `recipe.json`: editable authored footprint and route specifications, in tile coordinates.
- `blockout.json`: expanded planning data, water grades, roads, ground levels and independently traversable quest-route examples.

The image map begins at pixel [72,168] and is 1536×1344. North is up. Rulers show every four tiles; building rectangles represent ground footprints, not roofs or complete sprite bounding boxes. The sanctuary's 8×5 and workshop's 5×3 rectangles are provisional space reservations requiring their own designs. Later sprite placement must reserve roof, tree and character overhangs around these ground rectangles.

## Geography and opening quests

The northwest sanctuary has a raised courtyard with a southern stair connection. A two-tile upper lane passes Mira's workshop, crosses the stream and reaches the mill and Halden's storehouse yard. A western village lane and an eastern bank lane join at a second, southern bridge near Elira. This loop connects the central-west commons and eastern cultivated terrace without a single mandatory crossing choke point.

| Place | Ground footprint | Proposed function |
| --- | --- | --- |
| Sanctuary | [11,7,8,5] | Bedroom, breakfast, Serene's request and return; separate interiors remain to be designed |
| Mira's workshop | [24,15,5,3] | MQ02 contact near the upper crossing; new landmark placeholder |
| Watermill | [40,11,4,3] | Existing mill's nominal ground footprint; front-right wheel reserved against the west-flowing race |
| Halden | [40,23,4,3] | Standard 13×10 separate interior; sack task at the entry/storehouse yard |
| Elira | [27,37,3,3] | Approved compact 10×10 interior and lantern task near the main bridge |
| Venn | [49,27,5,3] | Wide 16×10 separate interior, recovering child's sleeping area, nearby gate and plots |
| Commons | [15,32,12,8] | Flexible 12×8 gathering space for daily activity, Aldric's visit and the festival |

Three additional standard cottages give the village a small residential cluster. Gardens and growing plots are schematic space reservations. Props, households and crowd positions have not been invented for the unnamed homes.

MQ01 begins at the sanctuary and visits Halden first with Tomas. Tomas returns by the upper crossing. Elira and Venn can be visited in either order before returning to Serene. Both sequences are exported; the image draws one purple example to avoid overlapping two identical sets of paths. The marker numbers 3/4 identify the homes, not a forced order. The gate is marked G. Elira's shelf/lantern and the Venn child's bed are interior interactions, not objects placed outdoors in this diagram.

MQ02 can visit Mira and the mill before taking the northbound maintenance path to a separate woodland map. The obstruction, encounter design and final scene staging remain open. The north exit is an available planning connection; no artificial MQ01 roadblocks are proposed. Quest progression remains a matter of dialogue/state rather than locking village routes.

The south road supports Aldric's arrival at the commons. The commons, main bridge and sanctuary courtyard can host changing festival dressing while preserving the established circulation. Festival mechanics, exact performances, stalls and named NPC positions remain future decisions.

## Elevation and water contract

L1 is the village and both stream bridge approaches. L2 contains the sanctuary terrace and eastern cultivation terrace. L3 is the northern headwater upland. These are relative planning units, not approved sprite pixel heights or a reinterpretation of the watermill's existing elevations. Stone boundaries mark height changes; routes change levels only through the four marked stair rectangles.

The main brook descends from a water surface of 2.8 in the upland to 0.8 entering the village, then gently falls to 0.33 at the south boundary. All water surfaces remain below their adjoining ground level. Heights only decrease downstream.

The brook and two independently controlled supplies enter from the northern woodland map. Their headwater intake junctions are beyond this blockout's north edge; the town diagrams mark the connections rather than inventing the final woodland puzzle layout. This leaves a credible upstream location for MQ02's obstruction outside the village:

1. The **mill race** enters at [43,0] with height 2.8, descends through its own northern supply ledge, turns east and south around the mill, then flows west beneath the front-right wheel to return at [34,15] with height 0.73. The service landing crosses this race separately from the two stream bridges. Its current direction agrees with the approved clockwise wheel. Interrupting this branch upstream does not stop the village brook or Venn irrigation supply.
2. The **irrigation supply** enters at [60,0] with height 2.8, then drops to the L2 terrace at [60,6]. It descends gently through the south-flowing Venn gate at [60,27], then falls through a visible field spillway at [60,36] onto L1. A lower drain returns to the brook at [35,48], height 0.4. It never climbs a terrace wall or crosses a pedestrian lane without a designated crossing.

Thin channels reserve a full tile corridor in this blockout; their blue cells are not a proposal to widen the approved eight-pixel channel artwork. The final dressed map must register the existing art's narrower water band, banks, gate ports and mill contact precisely.

The full 64×56 boundary is the first sizing hypothesis. This blockout prioritizes checking circulation, water and household relationships. Walking pace, camera framing, dense foliage, roof occlusion, bridge-rail drawing order and precise outdoor task props need a later playable-scale review. No movement-time promise is made from tile distances alone.

## Rebuild and checks

```sh
PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/project-jrpg/bin/python tools/build_eldenmere_blockout.py
PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/project-jrpg/bin/python tools/test_eldenmere_blockout.py
```

Uses the existing Pillow environment and system DejaVu Sans fonts. The four checks independently verify dry, disjoint native building footprints; descending water grades and downstream joins; level bridge ends; and graph access to all nine doors, gate, storage, commons and both exits. This is planning validation on 24px cells, not installed game navigation or full sprite/camera clearance.

Narrative references: [approved opening quest](../../../narrative/game_01/CH01_MQ01.md) and [Chapter 1 structure](../../../narrative/game_01/CHAPTER_01.md). The geographic design is approved. Exact interactive scene staging remains future work.
