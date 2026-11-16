"""Logical-scale Caelan references for old terrain/prop review recipes.

No retired artwork is loaded. Historical reference names select current HD
art through the runtime registry, sampled explicitly for a 1x review canvas.
Gameplay must use rendering.load_art instead to retain native detail.
"""
from pathlib import Path
import json
import re
import hashlib
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def reference_digest(path):
    """Current file hash, or recorded provenance for an explicitly retired input."""
    path = Path(path)
    if path.exists():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    relative = path.resolve().relative_to(ROOT).as_posix()
    ledger = json.loads((ROOT / 'assets/characters/caelan/retired_travel.json').read_text())
    for record in ledger['removed_files']:
        if record['path'] == relative:
            return record['sha256']
    raise FileNotFoundError(path)


def open_image(path, *args, **kwargs):
    if isinstance(path, (str, Path)):
        candidate = Path(path)
        try:
            relative = candidate.resolve().relative_to(ROOT).as_posix()
        except ValueError:
            relative = candidate.as_posix()
        idle = re.fullmatch(r'(?:assets/characters/caelan|assets/source/characters/caelan/overworld_refresh/legacy)/idle_(front|back|left|right)\.png', relative)
        walk = re.fullmatch(r'assets/characters/caelan/walk_(front|back|left|right)/frame_0([1-4])\.png', relative)
        if idle or walk:
            registry = json.loads((ROOT / 'assets/characters/caelan/animation.json').read_text())
            if idle:
                record = registry['idles'][idle[1]]
                file = ROOT / record['file']
                size = record['logical_size']
            else:
                bank = ROOT / registry['walks'][walk[1]]['manifest']
                data = json.loads(bank.read_text())
                file = bank.parent / data['frames'][(int(walk[2])-1)*4]['file']
                size = data['logical_size']
            with Image.open(file) as image:
                return image.convert('RGBA').resize(tuple(size), Image.Resampling.NEAREST)
    return Image.open(path, *args, **kwargs)
