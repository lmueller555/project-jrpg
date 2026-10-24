# Eldenmere dialogue portraits

Status: awaiting user review. Ten neutral-expression bust portraits cover the
four existing named characters and all six generic NPC palettes. The sage
female portrait is also used by the sanctuary gardener.

`portraits.json` maps speaker IDs to individual 72×72 opaque RGB PNGs. These
are intended for the proposed 72×72 image area inside the dialogue box's left
portrait pane. The background is dark green. They are not loaded by the game
yet; the dialogue box and click-to-advance behavior are a separate milestone.

Character references are the approved 24×36 sprites and source concepts.
Caelan retains chestnut hair and teal/cream/gold clothing; Mira retains her
ponytail, cream flower and pink shirt; Serene retains her bun, gray temples,
slate mantle and bronze clasp; Tomas retains blond hair, green eyes and rust
tunic. Male villagers use moss, rust and slate palettes. Female villagers use
blue/blue-eye, sage/green-eye and plum/hazel-eye palettes with low buns.

The new high-resolution portrait artwork was generated using the image
generation tool with those approved references. Original masters are preserved
in `assets/source/portraits/eldenmere/`. Exporting only crops the atlas cells
and samples them at 72×72 using nearest-neighbor resizing; it does not repaint
them. Both master sheets remain available for later size/layout revisions.

Rebuild exports and enlarged labeled review boards:

```sh
python tools/export_dialogue_portraits.py
```

The exporter requires Pillow and the DejaVu Sans system font for review labels.
The PNG assets themselves introduce no game runtime dependencies.

See [review boards](../../../docs/reviews/dialogue_portraits/README.md).
