# Fullscreen title screen — proposed design

Status: implemented for user review, including artwork, working logo, music
and title-menu behavior. Menu placement was revised to bottom center at the
user's request. See `docs/reviews/title_screen/README.md` for actual captures.
The final game name remains open; The Broken Covenant is a working title only.

## Composition

A broad dawn view across Eldenmere from the bridge approach. The brook curves
from the near foreground toward the watermill and village. Cottages with warm
windows and chimney smoke occupy the middle distance. The sanctuary sits on
the right-hand rise; distant wooded hills and mountains complete the horizon.
An upstream path disappears into the trees, suggesting the coming journey.

A festival lantern beside the foreground bridge provides a recognizable focal
detail. Caelan and Tomas stand together on the bridge as small figures,
with their approved clothing colors and relative heights.

Use a widescreen 16:9 composition, with a central safe region for the logo and
menu on other aspect ratios. A 640×360 pixel-art master is a useful title-art
target (3× at 1920×1080, 4× at 2560×1440). This uses a separate title renderer;
the implemented world canvas remains 480×320 with integer scaling and borders.
Do not enlarge the native terrain tiles or character frames to change their scale.

## Logo and menu

The cream-and-gold title is centered in the upper sky. A vertical menu sits
at the bottom center on a translucent dark-green panel. Background art covers
the display while UI fits separately, keeping every menu option visible.

- New Game
- Continue (only enabled when an implemented save system finds a valid save)
- Settings
- Quit

Mouse hover brightens an entry and moves a small lantern marker beside it.
Click activates it; keyboard navigation remains available. Settings exposes
display mode, title music on/off and Back.

## Motion and sound

Coordinate leaf/reed movement and chimney smoke with the existing 5.4-second
breeze. Add slow brook highlights, the mill wheel, subdued lantern flicker and
an occasional distant bird. Keep the camera still to preserve readable menus.

A new original sampled piano/cello title theme is implemented in fixed-tempo
4/4, replacing the discarded synthesized flute/harp score. See the timing audit
and clean/metronome excerpts in `docs/reviews/title_piano_cello/`.
Stream ambience and a distant sanctuary bell remain possible later additions.

New Game fades through black into the existing playable town. The approved
opening bedroom sequence remains a future story milestone. Title scene animation,
music, menu controls and game lifecycle integration are ready for this review.
