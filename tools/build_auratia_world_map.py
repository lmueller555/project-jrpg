"""Export the generated classroom map prop at its authored native sprite size.

The full-size map is the approved PNG and is never resized or rewritten here.
Only the separately generated prop source is cropped to its alpha bounds and
sampled with nearest-neighbor scaling for the existing classroom wall slot.
"""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/world/auratia/wall_map_generated.png'
OUTPUT = ROOT/'assets/world/auratia'
APPROVAL = ROOT/'assets/source/world/auratia/approval.json'
NATIVE_SIZE = (42, 40)
PROP_BOUNDS = (40, 36)


def build(check=False):
    approval_bytes = APPROVAL.read_bytes()
    approval = json.loads(approval_bytes)
    approved = OUTPUT/'world_map.png'
    if approval['world_map'] != approved.relative_to(ROOT).as_posix():
        raise ValueError('Approval does not identify the canonical world-map path.')
    approved_bytes = approved.read_bytes()
    approved_sha = hashlib.sha256(approved_bytes).hexdigest()
    if approved_sha != approval['world_map_sha256']:
        raise ValueError('World-map artwork differs from the approved source.')
    with Image.open(approved) as image:
        approved_size = list(image.size)
    if approved_size != approval['world_map_size']:
        raise ValueError('World-map dimensions differ from the approval record.')
    if approval['wall_sprite_source'] != SOURCE.relative_to(ROOT).as_posix():
        raise ValueError('Approval does not identify the classroom prop source.')
    source_bytes = SOURCE.read_bytes()
    source_sha = hashlib.sha256(source_bytes).hexdigest()
    if source_sha != approval['wall_sprite_source_sha256']:
        raise ValueError('Classroom prop differs from its recorded source.')
    if approval['wall_sprite_geography_sha256'] != approved_sha:
        raise ValueError('Classroom prop references a different world-map revision.')
    with Image.open(SOURCE) as image:
        source = image.convert('RGBA')
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
    manifest = {
        'id': 'auratia.world_map',
        'status': 'approved world map and derived classroom sprite adaptation',
        'revision': approval['revision'],
        'approval': APPROVAL.relative_to(ROOT).as_posix(),
        'approval_sha256': hashlib.sha256(approval_bytes).hexdigest(),
        'world_map': approved.relative_to(ROOT).as_posix(),
        'world_map_size': approved_size,
        'approved_original_filename': approval['approved_original_filename'],
        'world_map_sha256': approved_sha,
        'wall_sprite': (OUTPUT/'wall_map.png').relative_to(ROOT).as_posix(),
        'wall_sprite_size': list(NATIVE_SIZE),
        'wall_sprite_source': SOURCE.relative_to(ROOT).as_posix(),
        'wall_sprite_source_size': list(source.size),
        'wall_sprite_source_crop': list(bounds),
        'wall_sprite_source_sha256': source_sha,
        'wall_sprite_original_filename': approval['wall_sprite_original_filename'],
        'wall_sprite_geography_sha256': approved_sha,
        'export': 'crop opaque bounds; nearest-neighbor fit within 40x36; 64-color palette; centered in 42x40; binary alpha',
        'build_tool': 'tools/build_auratia_world_map.py',
        'geography': 'docs/narrative/world/WORLD_ATLAS.md',
        'polar_regions': 'docs/narrative/world/POLAR_REGIONS.md',
    }
    stream = BytesIO()
    native.save(stream, format='PNG')
    products = {
        OUTPUT/'wall_map.png': stream.getvalue(),
        OUTPUT/'map.json': (json.dumps(manifest, indent=2)+'\n').encode('utf-8'),
    }
    for path, content in products.items():
        if check:
            if not path.is_file() or path.read_bytes() != content:
                raise ValueError(f'Stale world-map export: {path.relative_to(ROOT)}')
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    verb = 'Verified' if check else 'Exported'
    print(f'{verb} Auratia classroom wall map at 42x40; approved full-size PNG preserved.')
    return native


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true',
                        help='Validate approved inputs and compare exports without writing.')
    build(check=parser.parse_args().check)
