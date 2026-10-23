# Eldenmere — animated irrigation channels

Status: draft artwork for user review. This milestone adds earth-lined channels, directed currents, stream intakes and small outlet trickles beside the approved terrain.

Tiles remain 24×24. The channels carry eight pixels of water, a one-pixel shallow rim inside the water and two pixels of earth on either side. All colors come from the approved ground/water palette. Six phases at 200 ms each match the stream's 1.2-second loop. Small current marks travel two native pixels per phase; channel walls stay stationary. Outlet droplets and small receiving puddles provide additional motion.

## Review

- `review_scene.gif`: the enlarged updated scene, with the stream feeding a connected channel network below the original review area.
- `channels_closeup.gif`: the channel area at 4× scale, with Mira and a female NPC for scale.
- `modules_review.gif`: all 40 directed modules animated together, labeled with connection mask and input/output ports.
- Matching `.png` files show the first phase of each review.
- `review_scene_frame_01.png`–`review_scene_frame_06.png`: native 480×528 scene frames.
- `review_scene.json`: ground choices, base stream-scene reference, directed channel placements, character placements and playback timing.

The review layout contains one stream intake, two splitting junctions, bends, straight runs and three trickling outlets. It extends the earlier scene by six tile rows; Mira and one NPC move onto dry ground beside the network. Existing character sprites, stream and ground exports are unchanged. The layout is an illustrative flow/scale test, not a canonical Eldenmere map or playable irrigation system. Gates, stone terraces, bridges and the mill remain later milestones.

## Native exports

- `frames/frame_01.png`–`frame_06.png`: six 192×120 atlases, eight columns by five rows, 40 modules per phase.
- `irrigation.png`: those atlases stacked into a 192×720 sheet: 240 composed tile frames.
- `channel_banks.png` and `channel_masks.png`: stationary 96×96 atlases indexed by cardinal connection mask. Slot zero is transparent; slots 1–15 cover every connected-port shape.
- `tileset.json`: module rectangles, directed input/output ports, source bank/mask paths, six frame references and timing.
- `palette.json`: the reused approved material colors with this pack's independent draft status.

The 40 modules comprise **32 directed routes over 15 connection shapes, four intake orientations and four outlet orientations**. Selecting each possible input for a shape supplies reverse-flow straights/bends and every junction input. Single-port channel modules are closed settling caps; special outlet modules provide the open trickling ends.

## Connections and flow

These narrow modules use **four cardinal bits: N=1, E=2, S=4, W=8**. This is a separate convention from the eight-neighbor blob masks used by the grass/dirt and stream packs. A module has one input; its other connected ports are outputs. For example, `channel_10_from_e` carries water west through an east/west channel, while `channel_07_from_n` splits a northern input east and south.

An intake's input is `stream`; its directional port supplies the next channel. Place it across a straight stream bank, aligned to the neighboring channel. An outlet receives water through its named input and discharges toward `receiver`. Its direction names the discharge direction. Outlet metadata includes the small local effect bounds where droplets may move over the receiving earth.

Use one shared phase index for connected channels and stream water. Flow marks repeat every 12 pixels and advance two pixels per phase; the 24-pixel tile length preserves their spacing through tile boundaries. Input-side marks approach the hub; output-side marks leave it. These are baked art frames, not a water simulation. The review's routing graph confirms that every placed module is reachable from the intake and flows toward an outlet.

Rebuild and verify from the repository root:

```sh
python tools/build_eldenmere_irrigation.py
python tools/test_eldenmere_irrigation.py
```

The generated appearance reference, sampled earth strip, binary droplet source and stationary shape layers are retained under `../../../source/terrain/eldenmere/irrigation/`. The source recipe controls approval status and rebuilds deterministically.
