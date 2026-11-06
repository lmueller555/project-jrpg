# Elden Vale Sanctuary — detailed reserve art

`approved_preview.png` retains the design approved in chat: southern arrival
arch, limestone hall and slate-roofed cloister, western memorial grove, eastern
cave mouth and the separate surveyed limestone face within the reserve.

`clean_plate_generated.png` is an image-generation edit of that exact preview.
It removes the five human figures and the gardener's held watering can while
preserving the composition. Game actors replace those baked figures. The two
retained source images are never modified by the exporter; `art_recipe.json`
records their hashes and the native registration.

Run `python tools/build_elden_vale_sanctuary_art.py` to export, or add `--check`
to verify the shipped files. The source is uniformly reduced from 1536×1024 to
1152×768 with nearest-neighbor sampling, matching the game's local character
scale. Ground and overview share the same source pixels.

The depth silhouettes are polygon-masked copies of those exact native ground
pixels, with binary alpha and registered ground baselines. They let the
existing renderer sort a character in front of or behind the hall, trees and
entrance arch. The hall's door and cloister recesses have transparent openings;
the entrance arch is an open ring rather than a solid rectangular overlay.
These masks do not paint replacement scenery or supply collision. The separate
scene geometry owns walkable routes, object footprints and travel contacts.

No people, dialogue portrait, cave dungeon or excavation work is baked into
the clean plate. The cave mouth and intact surveyed seam remain separate
features, and all main paths remain free of decorative stairs.
