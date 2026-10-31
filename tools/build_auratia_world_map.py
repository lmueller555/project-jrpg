"""Export the generated classroom map prop at its authored native sprite size.

The full-size map is the approved PNG and is never resized or rewritten here.
Only the separately generated prop source is cropped to its alpha bounds and
sampled with nearest-neighbor scaling for the existing classroom wall slot.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/world/auratia/wall_map_generated.png'
OUTPUT = ROOT/'assets/world/auratia'
NATIVE_SIZE = (42, 40)
PROP_BOUNDS = (40, 36)


def build():
    source = Image.open(SOURCE).convert('RGBA')
    # Generated transparency is exported to the same binary-alpha convention
    # as the school's existing props; the small sprite has no soft fringe.
    source.putalpha(source.getchannel('A').point(lambda alpha: 255 if alpha >= 128 else 0))
    bounds = source.getbbox()
    if bounds is None:
        raise ValueError('The wall-map source has no opaque pixels.')
    prop = source.crop(bounds)
    prop.thumbnail(PROP_BOUNDS, Image.Resampling.NEAREST)
    # Keep the icon's palette modest without introducing dithered edge pixels.
    prop = prop.quantize(colors=64, method=Image.Quantize.FASTOCTREE).convert('RGBA')
    native = Image.new('RGBA', NATIVE_SIZE)
    native.alpha_composite(prop, ((NATIVE_SIZE[0]-prop.width)//2,
                                 (NATIVE_SIZE[1]-prop.height)//2))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    native.save(OUTPUT/'wall_map.png')
    approved = OUTPUT/'world_map.png'
    with Image.open(approved) as image:
        approved_size = list(image.size)
    manifest = {
        'id': 'auratia.world_map',
        'status': 'approved world map and classroom sprite adaptation',
        'world_map': approved.relative_to(ROOT).as_posix(),
        'world_map_size': approved_size,
        'approved_original_filename': 'exec-84160ef4-23a8-49eb-9aba-f8626924f576.png',
        'world_map_sha256': hashlib.sha256(approved.read_bytes()).hexdigest(),
        'wall_sprite': (OUTPUT/'wall_map.png').relative_to(ROOT).as_posix(),
        'wall_sprite_size': list(NATIVE_SIZE),
        'wall_sprite_source': SOURCE.relative_to(ROOT).as_posix(),
        'wall_sprite_source_size': list(source.size),
        'wall_sprite_source_crop': list(bounds),
        'wall_sprite_source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'export': 'crop opaque bounds; nearest-neighbor fit within 40x36; 64-color palette; centered in 42x40; binary alpha',
        'build_tool': 'tools/build_auratia_world_map.py',
        'geography': 'docs/world/WORLD_ATLAS.md',
        'polar_regions': 'docs/world/POLAR_REGIONS.md',
    }
    (OUTPUT/'map.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print('Exported Auratia classroom wall map at 42x40; approved full-size PNG preserved.')
    return native


if __name__ == '__main__':
    build()
