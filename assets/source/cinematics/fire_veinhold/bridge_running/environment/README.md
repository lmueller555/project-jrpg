# Lateral bridge layers

The whole-scene `background_generated.png` and `prompt.txt` retain the original
design reference. The combined painting is not loaded by the running shot.

Two registered image edits supply the active layers:

- `far_generated.png`: distant sky, mountains and sea, with the bridge removed.
- `bridge_generated.png`: the complete rail and deck, with transparent sky and
  sea, including the gaps between the rail braces.

Each source retains the same 2172×724 canvas. The exporter uniformly samples
the whole canvas to 1920×640, preserving registration. It removes only alpha≤1
quantization dust from otherwise transparent regions; it does not paint scenery,
reshape railings or segment the source into independently moving fragments.
The layer prompts, generation paths and source/output hashes are in `recipe.json`.

```sh
python tools/export_prologue_bridge_background.py
python tools/export_prologue_bridge_background.py --check
```

The distant layer stays fixed during this short shot. The complete bridge layer
follows camera travel at ground speed. Reduced Motion retains that ground/stride
relationship while removing the optional backward camera drift. The runtime
alternates mirrored background tiles so adjoining edges share their pixels;
this reflection applies only to scenery, never to character anatomy or costume.
Character animation and spacing are owned by the adjacent actor metadata and
the runtime `shot06/scene.json`.
