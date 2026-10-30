"""Export authored cinematic beacon props and upper sky without painting pixels.

Build dependencies: Pillow and NumPy. Generated source masters remain intact.
The exporter separates alpha-connected atlas cells, removes faint generation
matte, crops, nearest-resizes and registers the authored objects.
"""
from __future__ import annotations

from collections import deque
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/cinematics/beacon_props'
TARGET = ROOT/'assets/story/opening_cinematic/beacon_props'
ALPHA_MIN = 180


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(path):
    with Image.open(path) as image:
        size = list(image.size)
    return {'file': path.relative_to(ROOT).as_posix(), 'size': size,
            'sha256': digest(path)}


def atlas_components(image):
    pixels = np.asarray(image.convert('RGBA'))
    opaque = pixels[:, :, 3] >= ALPHA_MIN
    labels = np.zeros(opaque.shape, dtype=np.int16)
    height, width = opaque.shape
    components = []
    identifier = 0
    for y, x in zip(*np.nonzero(opaque)):
        if labels[y, x]:
            continue
        identifier += 1
        queue = deque([(int(x), int(y))])
        labels[y, x] = identifier
        left = right = int(x)
        top = bottom = int(y)
        area = 0
        while queue:
            px, py = queue.popleft()
            area += 1
            left, right = min(left, px), max(right, px)
            top, bottom = min(top, py), max(bottom, py)
            for nx, ny in ((px-1, py), (px+1, py), (px, py-1), (px, py+1)):
                if (0 <= nx < width and 0 <= ny < height
                        and opaque[ny, nx] and not labels[ny, nx]):
                    labels[ny, nx] = identifier
                    queue.append((nx, ny))
        if area < 5000:
            continue
        box = (left, top, right+1, bottom+1)
        crop = np.array(pixels[top:bottom+1, left:right+1])
        crop[:, :, 3] = np.where(
            labels[top:bottom+1, left:right+1] == identifier, 255, 0)
        components.append({'image': Image.fromarray(crop), 'bounds': list(box),
                           'opaque_source_pixels': area})
    return components


def registered(image, size, scale=None):
    """Use one scale for the lamp row and a common centered floor anchor."""
    if scale is None:
        scale = min(size[0]/image.width, size[1]/image.height)
    dimensions = (max(1, round(image.width*scale)),
                  max(1, round(image.height*scale)))
    if dimensions[0] > size[0] or dimensions[1] > size[1]:
        raise ValueError('Authored prop exceeds its registered canvas')
    resized = image.resize(dimensions, Image.Resampling.NEAREST)
    result = Image.new('RGBA', size)
    result.alpha_composite(resized, ((size[0]-dimensions[0])//2,
                                    size[1]-dimensions[1]))
    return result


def main():
    TARGET.mkdir(parents=True, exist_ok=True)
    names = ('upper_sky_generated.png', 'lamp_stages_generated.png',
             'sword_helmet_generated.png')
    original = {name: digest(SOURCE/name) for name in names}

    with Image.open(SOURCE/names[1]) as image:
        components = atlas_components(image)
    lamps = sorted((item for item in components if item['bounds'][1] < 400),
                   key=lambda item: item['bounds'][0])
    cups = [item for item in components if item['bounds'][1] >= 400]
    if len(lamps) != 4 or len(cups) != 1:
        raise ValueError('Expected four lamp states and one isolated cup')
    scale = min(18/max(item['image'].width for item in lamps),
                30/max(item['image'].height for item in lamps))
    extraction = {}
    for stage, item in enumerate(lamps):
        filename = f'lamp_{stage}.png'
        registered(item['image'], (18, 30), scale).save(TARGET/filename)
        extraction[filename] = {key: value for key, value in item.items()
                                if key != 'image'}
        extraction[filename]['native_scale'] = scale
    registered(cups[0]['image'], (6, 7)).save(TARGET/'cup.png')
    extraction['cup.png'] = {key: value for key, value in cups[0].items()
                             if key != 'image'}

    with Image.open(SOURCE/names[2]) as image:
        image = image.convert('RGBA')
        image.putalpha(image.getchannel('A').point(
            lambda value: 255 if value >= ALPHA_MIN else 0))
        bounds = image.getbbox()
        if bounds is None:
            raise ValueError('The sword and helmet source is empty')
        registered(image.crop(bounds), (100, 160)).save(TARGET/'sword_helmet.png')
        extraction['sword_helmet.png'] = {'source_bounds': list(bounds)}

    with Image.open(SOURCE/names[0]) as image:
        sky = image.convert('RGB').resize((960, 960), Image.Resampling.NEAREST)
    sky.save(TARGET.parent/'upper_sky.png', optimize=True)
    if original != {name: digest(SOURCE/name) for name in names}:
        raise AssertionError('A generated source changed during export')

    files = [TARGET/f'lamp_{i}.png' for i in range(4)]
    files.extend((TARGET/'cup.png', TARGET/'sword_helmet.png',
                  TARGET.parent/'upper_sky.png'))
    manifest = {
        'version': 1, 'exporter': 'tools/build_beacon_props.py',
        'sources': [record(SOURCE/name) for name in names],
        'exports': [record(path) for path in files], 'extraction': extraction,
        'registration': {
            'lamp_size': [18, 30], 'lamp_top_left': [615, 345],
            'lamp_floor_anchor': [9, 30], 'lamp_flame_world': [624, 363],
            'cup_size': [6, 7], 'cup_anchor': [3, 7],
            'cup_world': [648, 357], 'memorial_size': [100, 160],
            'memorial_anchor': [50, 160], 'memorial_world': [395, 430],
            'helmet_focus_world': [395, 295],
            'upper_sky_size': [960, 960], 'upper_sky_origin': [0, -640],
        },
        'notes': [
            'Four unlit authored lamp bodies show damage, frame repair, glass fitting and completion.',
            'The runtime supplies flame and glow independently of the repair-stage artwork.',
            'The anonymous steel helmet has dried blood stains; no owner or casualty identity is assigned.',
            'The sword is physically embedded in its stone base and belongs to the foreground plane.',
            'Upper sky contains only clouds and stars; no hidden cosmology is established.',
            'Alpha component extraction avoids including the nearby cup in a lamp cell.',
        ],
    }
    (TARGET/'provenance.json').write_text(json.dumps(manifest, indent=2)+'\n')

    review = Image.new('RGB', (600, 260), '#263142')
    draw = ImageDraw.Draw(review)
    for index in range(4):
        image = Image.open(TARGET/f'lamp_{index}.png').convert('RGBA')
        image = image.resize((72, 120), Image.Resampling.NEAREST)
        review.paste(image, (15+index*85, 38), image)
        draw.text((15+index*85, 17), f'Lamp {index}', fill='#eee8d2')
    image = Image.open(TARGET/'cup.png').convert('RGBA').resize((30, 35), Image.Resampling.NEAREST)
    review.paste(image, (143, 190), image)
    draw.text((15, 203), 'Bench cup', fill='#eee8d2')
    image = Image.open(TARGET/'sword_helmet.png').convert('RGBA')
    review.paste(image, (420, 54), image)
    draw.text((395, 22), 'Foreground memorial', fill='#eee8d2')
    review.save(ROOT/'work/beacon-props-contact.png')
    print(json.dumps({'exports': len(files), 'registration': manifest['registration']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
