# Retained source inputs for Caelan story actions

Ordinary travel uses the approved HD banks registered in
`assets/characters/caelan/animation.json`. The old 1× travel registration and
expanded PNG banks were removed; the old travel exporter is retired.

`actions_authored.png`, `dependents.json` and `legacy/dependents/` retain the
complete authored action drawings and original prop/FX inputs needed by existing
household, carrying, casting and rescue scenes. Some action recipes also sample
idle/walking body cells from `travel_authored.png`; that atlas is retained solely
as a reproducible source input for those unique scenes, not a runtime travel bank.
`tools.build_caelan_overworld` provides registration helpers without a travel
export entry point. Rebuilding those action drawings is a separate scoped task.

The global visual standard in `docs/VISUAL_ART_STANDARD.md` owns current art,
anatomy, registration and animation guidance. These source inputs and older
recipes describe historical implementation facts, not new construction rules.
