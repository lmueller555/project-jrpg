# Asset tools

The walk builder assembles character-specific source parts against retained semantic pose masks from Caelan's approved cycles.

```sh
python -m pip install -r tools/requirements-assets.txt
python tools/build_character_walk.py mira
python tools/build_character_walk.py mira --direction all
```

Run these commands from the repository root using Python 3.12. In the current cloud environment, `/workspace/.venvs/project-jrpg/bin/python` already has the dependency installed.

Use `--refresh-template` to regenerate shared masks before assembling the character. The builder reads the recipe, idle and approved reference sprites, writes derived template/source components when requested, and writes the frame PNGs, sheets, JSON and looping review GIFs. The source idle and approved references remain unchanged.

`--direction` accepts `front`, `left`, `right`, `back`, or `all`. Front remains the default. Each direction has its own appearance input, recipe and material masks. `all` also exports a combined native sheet, metadata, and labeled four-direction comparison GIF. Approval labels come from each recipe.

New characters need a recipe and appropriately prepared appearance parts. Shared semantic arm masks allow clothing recoloring; shared leg art requires matching trousers/boots. Other body proportions or costumes can use additional pose components rather than deforming a flattened idle image.
