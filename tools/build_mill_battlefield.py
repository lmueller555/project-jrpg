"""Export authored MQ02 riverbank scenery without painting new game artwork.

The imagegen panorama is resized at nearest-neighbour resolution. The isolated
fallen tree is alpha-trimmed, nearest-resized and registered in a native canvas.
Original generated sources are retained alongside their provenance README.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/combat'
BATTLEFIELD = ROOT/'assets/combat/millrace'
EVIDENCE = ROOT/'assets/story/mill/encounter'
BACKGROUND_SOURCE = SOURCE/'millrace_background_generated.png'
TREE_SOURCE = SOURCE/'millrace_fallen_tree_generated.png'
CANVAS = (480, 320)
TREE_CANVAS = (128, 96)
TREE_POSITION = (224, 184)


def source_record(path):
    with Image.open(path) as image:
        dimensions = list(image.size)
    return {'file': path.relative_to(ROOT).as_posix(),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'dimensions': dimensions}


def write(path, data):
    path.write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')


def main():
    BATTLEFIELD.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    with Image.open(BACKGROUND_SOURCE) as source:
        source.convert('RGB').resize(CANVAS, Image.Resampling.NEAREST).save(
            BATTLEFIELD/'background.png', optimize=True)
    with Image.open(TREE_SOURCE) as source:
        tree = source.convert('RGBA')
        alpha = tree.getchannel('A').point(lambda value: 255 if value >= 128 else 0)
        bounds = alpha.getbbox()
        if bounds is None:
            raise ValueError('Fallen-tree source has no opaque artwork')
        tree.putalpha(alpha)
        tree = tree.crop(bounds)
        tree.thumbnail((120, 88), Image.Resampling.NEAREST)
        native = Image.new('RGBA', TREE_CANVAS)
        native.alpha_composite(tree, ((TREE_CANVAS[0]-tree.width)//2,
                                     (TREE_CANVAS[1]-tree.height)//2))
        native.save(EVIDENCE/'tree_evidence.png', optimize=True)
        native_bounds = list(native.getbbox())
    write(BATTLEFIELD/'scene.json', {
        'id': 'upper_millrace_riverbank', 'canvas': list(CANVAS),
        'background': 'background.png', 'world_map': 'upstream',
        'camera_facing': 'south-southwest toward Eldenmere',
        'river': 'near left edge, curving alongside the bank',
        'source': source_record(BACKGROUND_SOURCE),
        'exporter': 'tools/build_mill_battlefield.py',
        'notes': [
            'Dry central riverbank leaves room for the Tusker and two party members.',
            'Distant northern cottages and the slate-roofed sanctuary identify Eldenmere.',
            'Freshly broken wood connects the encounter to the fallen intake limb.',
            'No actors, interface, festival props or actor shadows are baked into the art.'
        ]
    })
    write(EVIDENCE/'scene.json', {
        'id': 'millrace_fallen_tree', 'world_map': 'upstream',
        'image': 'tree_evidence.png',
        'canvas': list(TREE_CANVAS), 'draw_anchor': [0, 0],
        'position': list(TREE_POSITION), 'sort_y': 280,
        'opaque_bounds': native_bounds, 'collision': False,
        'source': source_record(TREE_SOURCE),
        'exporter': 'tools/build_mill_battlefield.py',
        'notes': [
            'Visual evidence beside the path; does not introduce an invisible blocker.',
            'The snapped bank-side tree has tusk gouges and a missing broken limb.',
            'The established intake-screen limb remains the actual repair obstruction.'
        ]
    })
    print(json.dumps({'background': list(CANVAS), 'fallen_tree': list(TREE_CANVAS),
                      'tree_position': list(TREE_POSITION), 'tree_bounds': native_bounds}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
