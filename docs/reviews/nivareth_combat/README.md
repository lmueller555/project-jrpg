# Nivareth combat art review

Nivareth is a pure Ice Aether elemental: a white crystal core suspended inside
curved frost-glass sheets and separated shard limbs. The pale blue/white mantle
uses cool dark edges to remain visible against the Stillfrost cave backdrop.
It has no biological body or face. Its precise movements unfold, fracture, and
reform its ice structure.

The pack has **176 unique authored drawings across ten states**. The full native
atlas is [spritesheet.png](../../../assets/combat/nivareth/spritesheet.png).
The [contact sheet](sprite_contact_sheet.png) samples eight poses from each
state. The [GIF](sprite_animations.gif) and [silent MP4](sprite_animations_silent.mp4)
show every authored pose in sequence, with a pale-background inset to check the
white core and cool outline. This is an authored-pose review, not a gameplay
recording. The reel samples authored durations at 25 FPS and lasts 10.76 seconds.

| State | Drawings | Authored duration | Contact |
| --- | ---: | ---: | ---: |
| Emerge | 8 | 800 ms | — |
| Idle | 16 | 1600 ms, loop | — |
| Rime Needle | 16 | 900 ms | 450 ms |
| Glassfall | 24 | 1400 ms | 800 ms |
| Gather Frost | 24 | 1400 ms | 700 ms |
| Charged hold | 16 | 1600 ms, loop | — |
| Frostspire Thrust | 24 | 1400 ms | 700 ms |
| Settling | 16 | 1200 ms, loop | — |
| Hurt | 8 | 400 ms | — |
| Defeat | 24 | 1800 ms | — |

The runtime canvas is 160×144 with a fixed floor at (72, 128). Per-frame core,
body, contact and cast-origin anchors share the sprite clock. The manifest has
direct state names and namespaced action aliases. Sources and their SHA-256
provenance are retained in `assets/source/combat/nivareth/`; the deterministic
exporter verifies binary alpha, no clipping, 64 colors, and 176 distinct poses.
`verification.json` records the review outputs and manifest hash.
