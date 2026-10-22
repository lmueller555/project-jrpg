# Male NPC — directional idle sources

Status: all three directional appearances and their palette variants are approved by the user in chat. The approved front idle is unchanged.

`turnaround_concept.png` is generated reference art for the same male NPC, ordered left, right, back. The approved brown-haired front design supplies the appearance; Caelan's idle turnaround supplies game scale and standing-pose references. These are stationary idles, not walking frames.

`export_idles.py` exports one 24×36 native brown-haired base per direction. It uses hard alpha, nearest-neighbor sampling and the original named material palette. Source bands align the head, shoulders, belt, trousers and boots to the front frame. Palette restrictions keep warm hair highlights out of the skin ramp; forearm/hand regions preserve skin colors. Each profile has one visible two-pixel-high eye, matching the front eyes' height. The back has no face.

`export.json` records source panels, alpha bounds, vertical registration, material choices and eye/skin regions. Rebuild from the repository root with asset dependencies installed:

```sh
python assets/source/characters/npcs/male_01/directions/export_idles.py
python tools/build_npc_palette_variants.py --direction all
```

The second command applies the existing rust/charcoal and slate/brown palettes to every direction, then exports native sheets, metadata and enlarged review boards. Palette variants share each direction's exact silhouette and pixel arrangement. Their standing frame uses the shared `[12, 34]` foot anchor. Approval statuses come from each frame's metadata and survive rebuilds.
