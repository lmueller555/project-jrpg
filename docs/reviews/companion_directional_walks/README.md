# Companion directional walking review

**Status:** Nine new left, right and rear walk cycles are proposed for user
review. The approved front walks appear alongside them as references.

[Watch all three characters in all four directions](walk_directions.gif).
[Inspect the authored key poses](contact_sheet.png).

| Character | Animated comparison |
| --- | --- |
| Lucan Rooke | [Front, left, right and rear walks](lucan_walk_directions.gif) |
| Rhea Sorel | [Front, left, right and rear walks](rhea_walk_directions.gif) |
| Edran Hale | [Front, left, right and rear walks](edran_walk_directions.gif) |

The new cycles contain 36 transparent 24×36 frames. Each cycle has four distinct
poses at 140 ms per frame, for a 560 ms loop matching the approved front walks.
The poses alternate contact, passing, opposite contact and opposite passing.
The enlarged comparisons use whole-number nearest-neighbor scaling and include
native-size examples.

The approved directional idles establish each costume and equipment side.
Lucan keeps his sword in his right hand and shield in his left. Rhea keeps
her staff and notebook pouch on her left and her dress slit on her right.
Edran carries his crook in his right hand and healer pouch on his left.
The profile cycles use separately authored near and far limbs and equipment.

Each cycle shares one palette from its approved front idle and one uniform
sampling scale and grid. Source poses supply the leg movement, passing rise,
cloth follow-through and prop motion. Read each animation's foot anchor when
rendering it; image padding does not determine the character's world position.

## Movement through Eldenmere

- [Left-facing movement](world_left.gif)
- [Right-facing movement](world_right.gif)
- [Rear-facing movement](world_back.gif)

These review captures temporarily stage Caelan and the three companions in the
actual town renderer, on collision-free routes at the game's walking speed.
The scenery remains still so the gait and foot placement can be compared.
Recruitment scenes and party behavior will use the movement sets after approval.

Generated sources, prompts and extraction recipes are retained under
`assets/source/companions/<character>/walk_<direction>/`.
The native frames and animation manifests are under the corresponding
`assets/characters/<character>/walk_<direction>/` paths.

Rebuild the exports and review captures with:

    python tools/build_companion_directional_walks.py
    python tools/capture_companion_directional_walks.py
