# Shared back-walk pose template

Four poses derived from Caelan's approved back walk, at 24×36 and 140 ms per frame. On passing frames 2 and 4, the source upper body is already raised by one pixel; consumers must not translate the arm masks again.

Each `frame_01`–`frame_04` directory contains screen-left/right semantic arm material masks and the exact paired lower-leg/boot pixels from rows 26–35. In profiles the two arm-mask files partition the projected arm pixels in screen space; they are not independent skeletal near/far bones. Material codes and phase references are defined by `poses.json`.

Profile extraction identifies sleeve/skin/cuff material regions and their immediate outline, excluding the source tabard and preserving the existing projected limb motion. Frontal/rear extraction uses the existing bounded arm regions. Character recipes supply the appearance-specific torso, hair, clothing colors and accessories.

Rebuild with `python tools/build_character_walk.py mira --direction back --refresh-template`. Approved reference artwork is read-only input.
