"""Export preserved, full-detail mountain layers for the Fire Veinhold opening.

The recipe permits native crops, alpha cleanup and transparent registration
padding. It never resizes scenery or constructs new terrain pixels.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/cinematics/fire_veinhold/shot01/environment'
TARGET = ROOT/'assets/story/fire_veinhold_opening/shot01/environment'
LAYERS = ('sky', 'distant', 'mid', 'foreground_a', 'foreground_b', 'crest')


def _png(image):
    buffer = BytesIO()
    image.save(buffer, 'PNG', optimize=False, compress_level=9)
    return buffer.getvalue()


def _source_path(source, filename):
    candidate = source/filename
    if Path(filename).is_absolute() or not candidate.resolve().is_relative_to(source.resolve()):
        raise ValueError('Mountain source files must remain inside the source directory')
    return candidate


def _integers(value, length):
    return isinstance(value, list) and len(value) == length and all(type(n) is int for n in value)


def products(source=SOURCE, target=TARGET):
    """Return deterministic output bytes without writing or changing sources."""
    source, target = Path(source), Path(target)
    recipe = json.loads((source/'recipe.json').read_text(encoding='utf-8'))
    if recipe.get('version') != 1 or recipe.get('density') != 2:
        raise ValueError('Mountain environment requires version one and artwork density two')
    if set(recipe['layers']) not in (set(LAYERS), {'panorama'}):
        raise ValueError('Mountain environment requires all six named depth layers')
    records = {}
    for record in recipe['source_records']:
        filename = record['file']
        if filename in records:raise ValueError('Duplicate mountain source record: '+filename)
        path = _source_path(source, filename)
        if sha256(path.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError('Mountain source changed without a recipe update: '+filename)
        records[filename] = record
    output = {}
    manifest = {'version':1, 'density':2, 'layers':{}}
    if 'framing' in recipe:manifest['framing'] = recipe['framing']
    for name in recipe['layers']:
        spec = recipe['layers'][name]
        filename = spec['source']
        if filename not in records:raise ValueError('Unrecorded mountain layer source: '+filename)
        with Image.open(_source_path(source, filename)) as original:
            image = original.convert('RGBA')
        crop = spec.get('crop', [0, 0, image.width, image.height])
        if (not _integers(crop, 4) or not 0 <= crop[0] < crop[2] <= image.width
                or not 0 <= crop[1] < crop[3] <= image.height):
            raise ValueError('Mountain layer crop is outside its preserved source: '+name)
        image = image.crop(crop)
        if 'alpha_threshold' in spec:
            threshold = spec['alpha_threshold']
            if type(threshold) is not int or not 0 <= threshold <= 255:
                raise ValueError('Mountain alpha threshold must be an integer from zero to 255')
            image.putalpha(image.getchannel('A').point(lambda alpha:255 if alpha >= threshold else 0))
        size = spec.get('canvas', list(image.size))
        offset = spec.get('offset', [0, 0])
        if (not _integers(size, 2) or min(size) <= 0 or not _integers(offset, 2)
                or min(offset) < 0 or offset[0]+image.width > size[0]
                or offset[1]+image.height > size[1]):
            raise ValueError('Mountain registration canvas must contain the complete native crop: '+name)
        if size != list(image.size) or offset != [0, 0]:
            canvas = Image.new('RGBA', size)
            canvas.paste(image, offset)
            image = canvas
        if image.getchannel('A').getbbox() is None:
            raise ValueError('Mountain depth layer is empty: '+name)
        # Alternate output directories are useful for reproduction checks;
        # runtime references still identify the checked-in canonical exports.
        record = {'image':(TARGET.relative_to(ROOT)/(name+'.png')).as_posix(),
                  'canvas':list(image.size)}
        if 'anchor' in spec:
            if not _integers(spec['anchor'], 2):raise ValueError('Mountain anchor must be two artwork pixels')
            record['anchor'] = spec['anchor']
        manifest['layers'][name] = record
        output[target/(name+'.png')] = _png(image)
    output[target/'art.json'] = (json.dumps(manifest, indent=2)+'\n').encode()
    return output


def build(check=False, *, source=SOURCE, target=TARGET):
    output = products(source=source, target=target)
    changed = [path for path, data in output.items() if not path.exists() or path.read_bytes() != data]
    if check and changed:
        raise ValueError('Stale prologue mountain exports: '+', '.join(path.name for path in changed))
    if not check:
        for path, data in output.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    build(check=parser.parse_args().check)
