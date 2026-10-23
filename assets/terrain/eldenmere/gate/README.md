# Eldenmere — animated irrigation gate

Status: approved following user review.

A small hand-lifted wooden sluice fits the approved eight-pixel irrigation channel. Weathered wood posts and a sliding board sit on warm-gray fieldstone footings, with restrained iron bands, a lifting handle and a locking pin. The crooked jammed panel and displaced pin support the Venn family's opening repair quest. The existing terrain/stone palette is reused exactly; new named wood and iron ramps provide the mechanism's materials.

## Review

- `review_scene.gif`: the updated 20×26-tile scene at 3×, with a caption above the world, 1440×1920 pixels.
- `gate_closeup.gif`: the gate, nearby characters, stairs, spillway and receiving channel at 5×, 840×1068 pixels including the caption.
- `states_review.gif`: open, closed and jammed states side by side at 8×, on the same six-phase water clock.
- Matching PNGs provide static first-phase previews.
- `scene_frames/frame_001.png`–`078.png`: native 480×624 frames without captions.

The 15.6-second scene demo shows the jammed gate, reseating the pin, raising the board, restored flow, lowering the board, closed flow and a staged return to the jammed pose for a seamless pose cycle. Captions identify each demonstration state. This is an art review sequence, not autonomous gate behavior or a playable repair quest.

Open water passes beneath the raised board. Closed water has calm upstream ripples and a dry bed immediately below the panel. Jammed water passes as a narrow trickle under the skewed board. A short delayed response carries filling/draining through the controlled channel branch and southern spillway; receiving basins retain small still pools when dry. The other branch continues flowing. These baked responses illustrate state changes rather than fluid simulation.

## Native assets

- `gate.png`: 144×252 sheet; seven animation rows, six 24×36 frames per row.
- `animations/<name>/frame_01.png`–`06.png`: 42 native sprite frames.
- `sprite.json`: frame rectangles, 200 ms timing, loop flags, lift/skew poses, ports and compatibility art.
- `downstream/dry_01.png`: static 72×72 atlas of the controlled downstream branch's dry channel/spillway pieces.
- `downstream/trickle_01.png`–`06.png`: six matching restricted-flow atlases.
- `palette.json`: named terrain, stone, wood and iron material ramps.
- `review_scene.json`: gate placement, controlled cells, delayed response modes, source scene, frame timeline and review framing.

Animation IDs are `idle_open`, `idle_closed`, `idle_jammed`, `opening`, `closing`, `repair` and `jamming`. The three idle states loop at six phases × 200 ms = 1.2 seconds; the four transitions play once. The board lifts eleven native pixels in six poses. Repair straightens its three-pixel skew and reseats the pin. Jamming supplies the reverse demonstration transition. Posts, crossbeam and stone bases stay fixed.

The prefab has a **24×24 ground footprint inside a 24×36 sprite**. The ground rectangle is `[0,12,24,24]`; the extra twelve pixels project north to show the standing mechanism. Place the ground rectangle over a north-input/south-output straight channel. Input and output remain eight pixels wide. The foot anchor is `[12,34]`. This first orientation is south-flowing; rotated views and collision/interaction logic remain separate work.

## Scene continuity and elevation

The gate is placed on the existing upper-level straight channel at tile `(11,18)`, with the sprite at native pixel `(264,420)`. Its controlled upper channel remains on the same terrace level. Water drops only at the existing southern spillway, then continues along the lower channel. The earlier review scene's northern boundary and all existing asset files are left as they were, following the user's instruction to retain that example while considering elevation in future work.

All native scene pixels outside the gate and its controlled downstream branch match the earlier terrace scene at the same water phase. Existing characters, walls, stairs, source assets and narrative are unchanged. The layout remains illustrative rather than canonical Eldenmere geography.

Rebuild with `python tools/build_eldenmere_gate.py`; check with `python tools/test_eldenmere_gate.py`. Approval state is read from the retained source recipe and survives rebuilds.
