# Western stone bridge art

`intact_generated.png` is an image-generated edit of the previous broken bridge:
the missing span is finished with continuous overhead stone paving and low
parapets. `destroyed_reference.png` preserves that original native PNG exactly;
the original composition asset and its authoring sources remain untouched.
`recipe.json` records source hashes, palette ownership and registered band cuts.

The exporter uses nearest-neighbour source sampling, the original 64-colour
stone/moss palette and binary alpha. All layers use a 288×144 canvas and
`[144,94]` anchor. The deck occupies local rows 34–105, leaving 72 native pixels
of clear paving; the far and near rails sort independently behind/in front of
travellers. The destroyed gap is transparent at columns 107–180 in every layer.
The restored state reuses the finished structure without assigning a repair
method or a story cause to its damage.

Reproduce from the repository root:

```sh
python tools/build_western_bridge_assets.py
python tools/build_western_bridge_assets.py --check
```

Runtime registration lives in `assets/terrain/overworld/elden_vale/bridge/art.json`.
The exporter supplies artwork only; regional travel, collision and quest
progression remain owned by the world and bridge-condition systems.
