# Companion directional idle review

**Status:** All nine left, right and rear poses are approved by the user,
completing the four-direction idle sets alongside the approved front poses.

[Compare all three characters](directional_comparison.png).

| Character | Four-view comparison |
| --- | --- |
| Lucan Rooke | [Front, left, right and rear](lucan_directional_idles.png) |
| Rhea Sorel | [Front, left, right and rear](rhea_directional_idles.png) |
| Edran Hale | [Front, left, right and rear](edran_directional_idles.png) |

Each view is a stationary overworld idle on a 24×36 transparent canvas. The
boards show whole-number nearest-neighbor enlargements and native-size
examples. These poses establish the directional silhouettes before the
remaining walking and running animations are drawn.

Equipment retains its anatomical side through each turn:

- Lucan carries his sword in his right hand and shield in his left.
- Rhea carries her purple staff in her left hand. Her dress slit is on her
  right thigh, and her notebook pouch is on her left hip.
- Edran carries his crook in his right hand and his healer pouch on his left.

Near and far equipment overlap the body according to the viewing direction.
The left and right views use separate authored drawings.

Each character shares the approved front idle's palette. Export records source
regions, uniform scale, foot registration and hashes alongside each PNG.
Use each pose's recorded foot anchor when rendering it. Rhea's rear pose has
extra padding for the staff on her left: its anchor is [12, 34], while her
front and side anchors are [10, 34]. This keeps her body on the same world
position when she turns.
The generated sheets and prompts are retained under
`assets/source/companions/<character>/directional_idles/`.

Rebuild the native poses and comparison boards with:

    python tools/build_companion_directional_idles.py

Recruitment scenes and party integration can now use these approved directional
references as their remaining movement and action animations are developed.
