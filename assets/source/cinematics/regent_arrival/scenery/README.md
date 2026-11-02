# Aldric's arrival: cinematic scenery sources

These original imagegen generations and revisions are retained unchanged.
`prompts.json` records each generation/edit instruction. The revised plates
keep the village sanctuary's humble timber belfry and register the intact
wooden town-brook bridge separately from the ruined western stone crossing.

The sanctuary revision lowers its window sill for the cinematic actor scale;
Serene's registered feet are `[625,335]` and her eye line clears the sill.
No people, horses, carts, text or UI are painted into the environment plates.
The isolated transparent wooden gate leaf supplies the checkpoint admission.

`tools/build_regent_arrival_scenery.py` performs deterministic native exports:

```sh
python tools/build_regent_arrival_scenery.py
python tools/build_regent_arrival_scenery.py --check
```

It uses only nearest resizing, transparent foreground-strip extraction and
alpha cleanup of the isolated gate prop. It never repaints an environment or
changes a source PNG. Runtime plates use a bounded 960×480 canvas; the game
views them through its ordinary 480×320 cinematic viewport.

The current Carrier conversation no longer uses the old riverbank acting area.
The separate [crossroads source](../crossroads/README.md) composes new native
scenery from retained raw materials against canonical region masks. It supplies
a bounded panorama, a 960×480 unscaled crossroads reference and a matching
bridge reference for the westward traverse. Old generated plates and their
runtime PNGs remain unchanged. The new builder is
`tools/build_regent_crossroads.py`; it is not an imagegen export.
