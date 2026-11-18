"""Reconstruct exact native walk pixels from the retained complete source."""
import hashlib
import json
from pathlib import Path
from PIL import Image

source = Path(__file__).resolve().parent
repo = next(p for p in source.parents if (p / 'AGENTS.md').is_file())
recipe = json.loads((source / 'recipe.json').read_text())
path = source / 'authored.png'
assert hashlib.sha256(path.read_bytes()).hexdigest() == recipe['source_sha256']
ref = repo / recipe['reference']
assert hashlib.sha256(ref.read_bytes()).hexdigest() == recipe['reference_sha256']
output = repo / 'assets/characters/npc_roster_hd/elder_woman_04/walk_right'
output.mkdir(parents=True, exist_ok=True)
with Image.open(path) as master:
    for index, (x, y, w, h) in enumerate(recipe['frames'], 1):
        master.crop((x, y, x+w, y+h)).save(output / f'frame_{index:02d}.png', optimize=True)
(output / 'spritesheet.png').write_bytes(path.read_bytes())
