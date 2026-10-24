# Fullscreen title screen — proposed design

Status: proposal for user review; artwork, logo, music and title-menu behavior
have not been implemented. Fullscreen gameplay startup is implemented separately.
The final game name remains open; The Broken Covenant is a working title only.

## Composition

A broad dawn view across Eldenmere from the bridge approach. The brook curves
from the near foreground toward the watermill and village. Cottages with warm
windows and chimney smoke occupy the middle distance. The sanctuary sits on
the right-hand rise; distant wooded hills and mountains complete the horizon.
An upstream path disappears into the trees, suggesting the coming journey.

A festival lantern beside the foreground bridge provides a recognizable focal
detail. Caelan and Tomas may stand together on the bridge as small figures,
with their approved proportions and clothing. Their inclusion is proposed.

Use a widescreen 16:9 composition, with a central safe region for the logo and
menu on other aspect ratios. A 640×360 pixel-art master is a useful title-art
target (3× at 1920×1080, 4× at 2560×1440). This would be a separate title renderer;
the implemented world canvas remains 480×320 with integer scaling and borders.
Do not enlarge the native terrain tiles or character frames to change their scale.

## Logo and menu

Leave open sky in the upper-left through upper-center for the cream and muted
gold title lettering. Place the menu on the quieter left side below the logo,
while the village remains visible across the center and right. A small dark
green panel or restrained translucent shade should provide predictable contrast.

- New Game
- Continue (only enabled when an implemented save system finds a valid save)
- Settings
- Quit

Mouse hover brightens an entry and moves a small lantern marker beside it.
Click activates it; keyboard navigation remains available. Settings could expose
display mode and audio levels once those settings are implemented.

## Motion and sound

Coordinate leaf/reed movement and chimney smoke with the existing 5.4-second
breeze. Add slow brook highlights, the mill wheel, subdued lantern flicker and
an occasional distant bird. Keep the camera still to preserve readable menus.

A proposed soft flute/plucked-string theme with flowing-water ambience and a
distant sanctuary bell should suggest home and curiosity. Audio is not available
yet; this is a direction for later creation, not a description of existing assets.

New Game would fade the vista into the approved opening bedroom scene once that
story sequence is implemented. First review a still scene with logo/menu placement,
then add animation and finally connect the title menu to the game lifecycle.
