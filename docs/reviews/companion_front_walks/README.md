# Companion front-walk animation review

**Status:** All three four-frame front-walk cycles are approved by the user.
The character standing designs remain approved.

[Watch all three walks beside Caelan](front_walks.gif).
[Watch movement through Eldenmere](walking_in_eldenmere.gif).
[Inspect the four poses beside each approved idle](contact_sheet.png).

| Character | Animated review | Motion direction |
| --- | --- | --- |
| Lucan Rooke | [Lucan loop](lucan_front_walk.gif) | Controlled stride; sword and shield held clear of his steps |
| Rhea Sorel | [Rhea loop](rhea_front_walk.gif) | Light stride; hair and skirt follow through; left-hand staff carried |
| Edran Hale | [Edran loop](edran_front_walk.gif) | Even stride; alternating boots beneath the blue robe; right-hand crook carried |

Each loop has four distinct 24×36 frames at 140 ms each, matching Caelan's
560 ms front-walk cycle. The phase order is screen-left contact, screen-left
support/passing, screen-right contact, screen-right support/passing. These
screen directions do not change anatomical equipment ownership.

The enlarged GIFs use nearest-neighbor scaling and show native-size sprites
below. Each character's approved idle is included in the individual preview.
The town preview uses the actual World.draw renderer on collision-free routes
at the game's 72-pixel-per-second walking speed. Scenery is held still to make
the actor motion easy to compare. It is a review capture, not a new
quest or a placement of the companions in the story.

The source-authored poses retain their generated sheets and prompts under
assets/source/companions. Export uses one common uniform scale per character,
body/pelvis registration and the approved idle's exact palette. Supporting
boots, equipment and cloth retain their authored shapes.

[Asset verification](validation.json) records timings, source hashes, frame
hashes, dimensions, registration and palette policy.
[World-preview verification](world_preview.json) records the renderer, route
and movement speed.

Rebuild all animations and previews with the repository's asset environment:

    python tools/build_companion_front_walks.py
    python tools/capture_companion_front_walks.py
