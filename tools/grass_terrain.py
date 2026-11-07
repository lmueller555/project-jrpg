"""Compile shared emerald materials without modifying archived source packs.

Only asset/map builders import this module. Runtime consumes the exported PNGs
and the shared interactive-grass manifest, without a Pillow dependency.
"""
from functools import lru_cache
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT/'assets/terrain/grass/assets.json'


def load_pack():
    return json.loads(PACK.read_text())


def material_images(manifest=None):
    manifest = load_pack() if manifest is None else manifest
    return {family: [Image.open(ROOT/path).convert('RGBA') for path in record['tiles']]
            for family, record in manifest['materials'].items()}


def material_at(x, y, family, images, *, seed=0):
    """Choose quiet growth plus small clusters of the two accent materials.

    Neighbouring cells share an accent mode, while native motifs vary within
    each patch. No per-pixel noise or runtime randomness is introduced.
    """
    patch = ((x//4+seed)*73856093) ^ ((y//3-seed)*19349663)
    local = ((x+seed)*83492791) ^ ((y-seed)*2971215073)
    if patch % 7 < 2 and local % 4 < 2:
        index = 2+(patch % 2)
    else:
        index = 1 if local % 5 < 2 else 0
    return index, images[family][index]


@lru_cache(maxsize=1)
def legacy_green_map():
    palette = load_pack()['palette']
    mappings = {}
    for old, names in (
        (ROOT/'assets/terrain/eldenmere/grass_dirt/palette.json',
         {'deep':'deep', 'shadow':'shadow', 'base':'base', 'light':'light'}),
        (ROOT/'assets/terrain/eldenmere/grass_flowers/palette.json',
         {'deep':'deep', 'shadow':'shadow', 'mid':'mid', 'base':'base',
          'light':'light', 'highlight':'highlight'}),
    ):
        data = json.loads(old.read_text())['materials']
        ramp = data.get('grass', data.get('greens'))
        for name, replacement in names.items():
            mappings[tuple(bytes.fromhex(ramp[name][1:]))] = tuple(bytes.fromhex(palette[replacement][1:]))
    return mappings


def remap_legacy_green(image, palette=None):
    """Replace exact archived grass/stem colours, preserving all other pixels.

    Soil, water, stone, petals and alpha remain unchanged. This also removes
    old olive tips embedded in bank/transition prefabs during composition.
    """
    mapping = legacy_green_map() if palette is None else palette
    converted = image.convert('RGBA')
    converted.putdata([(*mapping.get(pixel[:3], pixel[:3]), pixel[3])
                       for pixel in converted.getdata()])
    return converted
