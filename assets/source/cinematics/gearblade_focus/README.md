# Gearblade authored focus sources

`water_generated.png` contains eight authored world water-casting poses. Its Blue-only revision was edited with image_gen: the Blue gem and its spell glow remain, while the other three sockets are empty. The source layout and original poses are retained. The original reference commit and before/after source hashes are recorded in `../mill_gift/blue_only_edits.json`; the edited source is not an unmodified original.

Rebuild these world exports with `python tools/build_gearblade_focus.py --world-only`. This preserves the independently registered combat atlas and only updates the world frames, provenance and review contact sheet.
