"""Register authored imagegen scenery as native cinematic depth layers.

This exporter only crops, cleans alpha edges, nearest-resizes and registers
authored artwork. It does not paint scenery or modify the retained sources.
Run with the game's existing Pillow build dependency.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/source/cinematics/opening'
TARGET = ROOT / 'assets/story/opening_cinematic'
SIZE = (960, 480)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(path):
    with Image.open(path) as image:
        dimensions = list(image.size)
    return {'file': path.relative_to(ROOT).as_posix(),
            'dimensions': dimensions, 'sha256': digest(path)}


def pixel_alpha(image):
    """Remove faint matte residue without changing any authored RGB pixels."""
    image = image.convert('RGBA')
    image.putalpha(image.getchannel('A').point(lambda value: 255 if value >= 128 else 0))
    return image


def prop(image, box, size):
    result = pixel_alpha(image.crop(box))
    bounds = result.getbbox()
    if bounds is None:
        raise ValueError('The authored prop cell is empty')
    return result.crop(bounds).resize(size, Image.Resampling.NEAREST)


def main():
    TARGET.mkdir(parents=True, exist_ok=True)
    names = ('valley_generated.png', 'valley_alpha_generated.png',
             'sanctuary_generated.png', 'props_generated.png')
    before = {name: digest(SOURCE / name) for name in names}
    with Image.open(SOURCE / names[0]) as image:
        # The farthest plate intentionally retains terrain below the horizon:
        # it guarantees painted coverage behind the independently moving alpha
        # valley layer, including extreme camera positions.
        sky = image.convert('RGB').resize(SIZE, Image.Resampling.NEAREST)
    sky.save(TARGET / 'sky.png', optimize=True)
    with Image.open(SOURCE / names[1]) as image:
        valley = pixel_alpha(image).resize(SIZE, Image.Resampling.NEAREST)
    valley.save(TARGET / 'valley.png', optimize=True)
    with Image.open(SOURCE / names[2]) as image:
        sanctuary = pixel_alpha(image).resize(SIZE, Image.Resampling.NEAREST)
    with Image.open(SOURCE / names[3]) as image:
        half = image.height // 2
        bench = prop(image, (0, 0, image.width, half), (135, 26))
        lamp = prop(image, (0, half, image.width, image.height), (18, 30))
    sanctuary.alpha_composite(bench, (633, 350))
    sanctuary.alpha_composite(lamp, (615, 345))
    sanctuary.save(TARGET / 'sanctuary.png', optimize=True)
    # A shallow authored rubble strip sits below the acting plane and moves
    # only slightly faster than the architecture. The painted floor remains
    # underneath, preventing gaps during the restrained parallax.
    foreground = Image.new('RGBA', SIZE)
    foreground.alpha_composite(sanctuary.crop((0, 450, 960, 480)), (0, 450))
    foreground.save(TARGET / 'foreground.png', optimize=True)
    if before != {name: digest(SOURCE / name) for name in names}:
        raise AssertionError('An original generated source was modified')
    manifest = {
        'version': 1, 'canvas': list(SIZE),
        'exporter': 'tools/build_opening_cinematic_scenery.py',
        'sources': [record(SOURCE / name) for name in names],
        'exports': [record(TARGET / name) for name in
                    ('sky.png', 'valley.png', 'sanctuary.png', 'foreground.png')],
        'registration': {
            'actor_floor_y': 375, 'bench_rect': [633, 350, 135, 26],
            'bench_seat_y': 357, 'lamp_rect': [615, 345, 18, 30],
            'lamp_flame_center': [624, 363],
            'foreground_strip_y': 450,
        },
        'notes': [
            'Entirely imagegen-authored scenery; retained sources are unchanged.',
            'The farthest sky plate retains distant terrain as painted overscan.',
            'Alpha valley, architecture and near rubble are separate depth layers.',
            'The ordinary wayside sanctuary does not establish hidden cosmology.',
            'No people, dialogue, interface, flame or actor shadows are baked into scenery.',
            'The low shared bench supports actor seated poses at the registered floor.',
        ],
    }
    (TARGET / 'scenery_provenance.json').write_text(
        json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'canvas': SIZE, 'layers': len(manifest['exports']),
                      'registration': manifest['registration']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
