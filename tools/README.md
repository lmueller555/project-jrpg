# Asset tools

The front-walk builder assembles character-specific source parts against retained semantic pose masks from Caelan's approved cycle.

```sh
python -m pip install -r tools/requirements-assets.txt
python tools/build_character_walk.py mira
```

Run these commands from the repository root using Python 3.12. In the current cloud environment, `/workspace/.venvs/project-jrpg/bin/python` already has the dependency installed.

Use `--refresh-template` to regenerate shared masks before assembling the character. The builder reads the recipe, idle and approved reference sprites, writes derived template/source components when requested, and writes the frame PNGs, sheets, JSON and looping review GIFs. The source idle and approved references remain unchanged.

New characters need a recipe and appropriately prepared appearance parts. Shared semantic arm masks allow clothing recoloring; shared leg art requires matching trousers/boots. Other body proportions or costumes can use additional pose components rather than deforming a flattened idle image.
