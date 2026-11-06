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

The depth silhouettes copy those exact native ground pixels with binary alpha.
Every tree is registered to its own visible ground contact, including the
previously unlayered northern oak, grove saplings and cliff-side trees. The
hall, its western wall and the cloister have separate contacts. Benches, the
basin, planters, survey board, cave face and boundary stones also have layers.

Crown outlines exclude unrelated floor; the foliage palette gate removes pale
stone and bare path gaps while retaining dark wood. Trunks and main branches
have separate solid polygons. Door and arcade openings remain transparent, as
does the center of the arrival arch. Long sloping walls and rock faces are cut
into narrow strips following an authored ground-edge profile, so one end does
not inherit the other end's depth. Source coordinates are 1536×1024; the
exporter scales their visible front contact edges by 0.75 into the renderer's
native ordering space. It removes obsolete generated depth files on rebuild.

These masks do not paint replacement scenery or supply collision. The separate
scene geometry owns walkable routes, object footprints and travel contacts.

No people, dialogue portrait, cave dungeon or excavation work is baked into
the clean plate. The cave mouth and intact surveyed seam remain separate
features, and all main paths remain free of decorative stairs.
