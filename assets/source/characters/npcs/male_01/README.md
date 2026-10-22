# Male NPC 01 — appearance source

Status: male variant 01 is approved by the user in chat. Color variants 02 and 03 await review.

`idle_front_concept.png` is the generated appearance source. Caelan and Mira were used as style and proportion references. Their artwork is unchanged.

`export_idle.py` exports the concept into a 24×36 native frame with hard transparency and a restricted material palette. It crops to the alpha bounds at threshold 128, fits the same occupied 14×34 region as the reference characters, samples with nearest-neighbor and maps colors to the named palette. `export.json` records those export settings. This is an appearance export, not a walking-frame generator.

Rebuild from the repository root with the asset dependencies installed:

```sh
python assets/source/characters/npcs/male_01/export_idle.py
```

The export also creates a 24× review image and a 16× comparison with Caelan and Mira. The first NPC palette is brown hair, moss-green shirt, tan trousers and brown boots. Walking poses and other directions will be prepared after appearance approval.

`palette_variants.json` defines the other two color schemes and material regions. Rebuild those native frames and the comparison with `python tools/build_npc_palette_variants.py`. Only matching colors inside the named regions are replaced, so hair recoloring preserves brown clothing accents and boots.
