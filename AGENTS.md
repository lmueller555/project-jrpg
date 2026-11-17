# Repository instructions

Before designing or substantially revising a world, region, zone or environmental
scene, read the
[world and environment design standard](docs/WORLD_DESIGN_STANDARD.md).
It is the single reference for creative place-design principles and the design
brief: identity, inhabited landscapes, weather/phenomena, ruins, giant remains,
folklore and exploration. Approved lore, geography and revelation limits retain
their authority; illustrative concepts are not new canon. Use the companion art
standards below for construction and rendering.

For Elden Vale, use [the regional design guidance](docs/world/regions/ELDEN_VALE.md)
as the single creative brief for the region and Sanctuary approach. It includes
the approved Pale Antlers/Rising Rain target and mandatory nonblocking antler
placement. The regional HD foundation and protected travel routes remain
authoritative. The Pale Antlers, Sanctuary presentation and selected old
causeway/ruins are integrated; Rising Rain remains staged. Gameplay guides and historical
recipes/reviews retain technical facts and evidence, not competing design rules.

Before creating or changing artwork, textures, sprites, animation, asset
builders, renderers or their tests, read the
[global visual art standard](docs/VISUAL_ART_STANDARD.md).
It is the single reference for visual style, artwork/world/display units,
density, sizing, rendering, directional anatomy, gait, registration, export and
review. Its approved target is 2× artwork density with existing logical sizes
and gameplay proportions. Full-scene 2× composition is implemented in
`rendering.py`; Eldenmere town, its southern inn/shop lane, town interiors and
upstream are integrated environments. Elden Vale's regional foundation uses the
explicit `hd_art_manifest` overlay built by `tools/build_elden_vale_hd_integration.py`
and phase-aware material composition in `regional_terrain_hd.py`; its staged
foundation bank is retained separately. Other regions and character-bank migrations
continue individually. The live town composer is `tools/build_eldenmere_hd.py`;
older full-town compilers must not overwrite its assembled map. The reserve,
cave approach, public hall and relief room are owned by
`tools/build_sanctuary_reserve_hd.py`; their legacy build commands forward to it. Use the
explicit drawing/transform adapters and native presentation described in the
standard; bare Pygame writes to the logical mirror lose detail. Apply changes to
the authorized scope. Older recipes and review notes retain local implementation
facts and history, not competing construction rules.

For terrain materials, transitions, vegetation, water, elevation, pack exports
and terrain integration, also read the
[terrain art and pack creation standard](docs/TERRAIN_ART_STANDARD.md).
It owns the complete terrain workflow and existing pack maintenance reference;
do not recreate parallel terrain-authoring READMEs.

Before changing Eldenmere's layout or dressing, also read the
[settlement framework](docs/TERRAIN_ART_STANDARD.md#eldenmere-settlement-framework).
Use its source-owned clearance contracts and the existing town composer. The
street pass, Serene household courtyard, workshop/mill yards, civic well/school
composition and five central household plots are integrated. Household props and
soil remain within their named parcel boundaries; eastern growing and southern
arrival composition remain separate work.
Only explicitly declared district prop supports add collision; other district
placements remain inactive. Preserve existing workstations and quest staging.

For object manipulation, scene staging and prop rendering, also read
[the character–object interaction standard](docs/OBJECT_INTERACTION_STANDARD.md)
and [personal-prop visibility](docs/PERSONAL_PROPS.md).

Apply the standard to the work in scope:

- Approach and face the object; perform a recognizable, naturally proportioned
  action; then snap/transfer the object at its authored cue.
- Reasonably close hands are sufficient. Do not stretch anatomy or move planted
  feet to satisfy exact-contact coordinates or older tests.
- Preserve one object owner/location, camera-appropriate occlusion, and coherent
  cleanup/restoration. Personal props disappear after use; deposited props stay
  at their world destination.
- Check actual scene frames for anatomy, intent, depth, and facing, alongside
  focused tests for transfers and lifecycle state. Summarize the validation in
  the PR; do not claim visual compliance solely from passing completion tests.

Within their respective scopes, the global standards supersede conflicting older
scene notes, recipes, tests and historical review prescriptions. Approved lore,
geography and revelation limits retain their authority. Retain historical evidence
and local implementation facts. Record other inconsistent existing interactions
for a scoped follow-up rather than silently expanding unrelated work.
