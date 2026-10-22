# Asset tools

The walk builder assembles character-specific source parts against retained semantic pose masks from Caelan's approved cycles.

```sh
python -m pip install -r tools/requirements-assets.txt
python tools/build_character_walk.py mira
python tools/build_character_walk.py mira --direction all
python tools/build_character_walk.py npcs/male_01
```

Run these commands from the repository root using Python 3.12. In the current cloud environment, `/workspace/.venvs/project-jrpg/bin/python` already has the dependency installed.

Use `--refresh-template` to regenerate shared masks before assembling the character. The builder reads the recipe, idle and approved reference sprites, writes derived template/source components when requested, and writes the frame PNGs, sheets, JSON and looping review GIFs. The source idle and approved references remain unchanged.

`--direction` accepts `front`, `left`, `right`, `back`, or `all`. Front remains the default. Each direction has its own appearance input, recipe and material masks. `all` also exports a combined native sheet, metadata, and labeled four-direction comparison GIF. Approval labels come from each recipe.

New characters need a recipe and appropriately prepared appearance parts. Shared semantic arm masks allow clothing recoloring; shared leg art can retain matching trousers/boots or use an explicit leg-color mapping. Other body proportions or costumes can use additional pose components rather than deforming a flattened idle image.

The base male NPC front walk uses the same arm and leg poses with an explicit `leg_palette` mapping for tan trousers and brown boots. A recipe with `shared_leg_costume: false` must supply that mapping; unmapped source colors are rejected. `preserve_waist: true` retains the original belt/buckle and upper-trouser pixels instead of synthesizing a waist. Both options are opt-in, preserving the existing Mira output. Character directories may use identifier components separated by `/`, such as `npcs/male_01`; absolute paths and traversal components are rejected.

Male NPC front-idle palette variants are rebuilt with `python tools/build_npc_palette_variants.py`. The builder reads the approved native `male_01` frame and the retained `assets/source/characters/npcs/male_01/palette_variants.json` recipe. Exact replacements within material regions preserve the silhouette, shading layout and transparency. Shade aliases include brown hair highlights exported with shared leather colors, while keeping the belt and boots unchanged. It writes variants 02 and 03, their enlarged previews, a native three-frame sheet and a labeled review comparison. Existing approval statuses are preserved on rebuild.

For all four male NPC idle directions, run `python tools/build_npc_palette_variants.py --direction all`. It recolors the retained base views, preserves each frame's existing approval status and exports per-character 96×36 sheets plus the combined 96×108 sheet and labeled 12× review grid. `--direction left`, `right` or `back` rebuilds only that direction's variants and metadata. The default remains `front` for compatibility.

To re-export the three new base appearances from their retained concept, first run `python assets/source/characters/npcs/male_01/directions/export_idles.py`. Its source-specific registration bands and palette/feature rules are recorded in the adjacent `export.json`. This appearance export does not generate walking poses or edit the approved front art.

Build the two front-walk palettes and a synchronized three-NPC review with `python tools/build_npc_walk_variants.py`. The helper derives recipes from the approved base walk, reads the existing palette overrides, uses each approved palette idle for the head/waist and calls the shared walk builder. It replaces shirt and trouser material colors while keeping the leg silhouettes, boots, skin, belt, phases and bob. Existing recipe approval statuses survive rebuilds. The base walk is read only.

Outputs include each variant's four native frames, sheet, metadata, posed source parts, static strip and looping previews. `assets/characters/npcs/male_walk_front_variants.png` is a native 96×108 sheet with variants as rows and phases as columns. Its JSON records timing, anchors and per-variant animation status; `_review.gif` shows all three in synchronized 16× columns and `_review.png` is the first phase. `--direction` can select another direction after its base walk is approved.

The base male NPC now has draft left, right and back walk recipes. Rebuild all base directions and the labeled four-direction comparison with `python tools/build_character_walk.py npcs/male_01 --direction all`. These use the already-approved directional idles and retained shared pose masks. The original front walk remains unchanged. The palette helper will derive each remaining direction after its base cycle is approved.
