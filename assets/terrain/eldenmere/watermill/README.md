# Eldenmere — watermill

Status: draft artwork for visual review.

A compact gristmill combines a muted slate roof, timber-framed cream walls, wood-framed windows and a fieldstone foundation. The front-left doorway opens onto a small timber service landing over the race. An eight-spoke, eight-paddle wheel turns on the front-right axle. The roof, windows, masonry and landing stay still; the wheel, restrained splash accents, trailing drops and small downstream ripples animate.

## Review previews

- `review_scene.gif`: running mill in the updated 30×26-tile scene, native 720×624 enlarged 3× to 2160×1872.
- `mill_closeup.gif`: mill, supplied race, landing and scale NPC at 4×, 864×960.
- `states_review.gif`: running and stopped states side by side at 3×, 1392×832, including the upstream blockage.
- `stopped_scene.gif` and `stopped_closeup.gif`: matching reviews with the supply interrupted and wheel stationary.
- Matching PNGs provide static first-phase alternatives.
- `scene_running/` and `scene_stopped/`: six native frames for each state.

The review extends the approved bridge scene to the east. An intake leaves the brook upstream, carries water east and then south around the mill, turns west below the wheel and returns to the brook downstream. A gray-haired generic NPC is moved from the earlier example to the landing for scale; this is not a new named-character design. Existing Caelan, the bridge, irrigation gate and terrace remain intact. The scene is illustrative rather than a canonical Eldenmere map or implemented quest.

## Water, elevation and motion

The bank, mill floor and service landing share elevation **24**. Authored water-surface levels fall gently from **18 at the intake**, through **17 beneath the wheel**, to **16 at the brook return**. Every successive race cell is at the same or a lower water level. The axle is at 40 with a radius of 24, putting paddle tips at 16, just below the supplied race surface. The landing spans the eight-pixel channel at floor level; water passes beneath it. There are no stairs, uphill water routes or top-fed wheel falls.

The underside current moves **east to west**. The wheel rotates **clockwise as viewed**, so its lower paddles also move west, with wet paddles rising on the left. Native phases advance **7.5° every 200 ms**. Eight identical paddles give a 45° visual symmetry: the six-phase sprite loop repeats after 1.2 seconds while the implied full physical revolution takes 9.6 seconds. The existing stream and channels use the same six-phase clock.

The stopped review uses a small optional pebble/twig blockage in the upstream race. The supplied section remains wet; the channel beyond it is exposed, the wheel holds phase zero and all mill splash/drip effects disappear. The main brook and other approved water features continue independently. This is a baked art state, not a fluid simulation; final quest staging and the precise obstruction remain narrative/map decisions.

## Native assets

- `building.png`: fixed 144×168 layer, including the extracted building and 48×24 timber service landing.
- `wheel/frame_01.png`–`06.png`: six 48×48 native rotating-wheel frames.
- `effects/frame_01.png`–`06.png`: separate 144×168 splash, drop and ripple overlays.
- `running/frame_01.png`–`06.png`: complete 144×168 running prefabs.
- `stopped.png`: fixed structure plus the stationary wheel, without moving-water effects.
- `mill_sheet.png`: running phases stacked into 144×1008, six columns × 42 rows of 24-pixel sprite cells.
- `race/frame_01.png`–`06.png`: native compatibility atlases for the directed race and brook connectors.
- `race/dry.png`, `race/blocked.png`: dry channel pieces and the blocked-supply tile.
- `mill.json`: wheel angles/paddle centers, source rectangles, timing, layers, race pieces and elevation contract.
- `palette.json`: existing approved material ramps plus muted roof and window-glass colors.
- `review_scene.json`: exact source frames, race graph/grade, state modes, placements and review framing.

The complete prefab is six by seven 24-pixel sprite cells; the building's nominal ground footprint is four by three cells. The native 24×36 character art is unchanged. The mill overlay origin and its wheel/landing rectangles are recorded in metadata; place it only where the race contact band reaches the bottom paddles. Draw the race behind the mill and the scale/interactive characters afterward. Collision, interiors, interaction and playable map integration remain future work.

Rebuild with `python tools/build_eldenmere_watermill.py`; verify with `python tools/test_eldenmere_watermill.py`. Approval status is read from the retained source recipe. Earlier assets and narrative files are unchanged.
