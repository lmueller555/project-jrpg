# Male NPC 01 — appearance source

Status: draft awaiting user review.

`idle_front_concept.png` is the generated appearance source. Caelan and Mira were used as style and proportion references. Their artwork is unchanged.

`export_idle.py` exports the concept into a 24×36 native frame with hard transparency and a restricted material palette. It crops to the alpha bounds at threshold 128, fits the same occupied 14×34 region as the reference characters, samples with nearest-neighbor and maps colors to the named palette. `export.json` records those export settings. This is an appearance export, not a walking-frame generator.

Rebuild from the repository root with the asset dependencies installed:

```sh
python assets/source/characters/npcs/male_01/export_idle.py
```

The export also creates a 24× review image and a 16× comparison with Caelan and Mira. The first NPC palette is brown hair, moss-green shirt, tan trousers and brown boots. Walking poses and other directions will be prepared after appearance approval.
