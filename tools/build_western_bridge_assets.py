"""Export registered native bridge layers from preserved/generated source art."""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/terrain/overworld/elden_vale/bridge'
TARGET = ROOT/'assets/terrain/overworld/elden_vale/bridge'
PHASES = ('intact', 'destroyed', 'restored')


def _png(image):
    stream = BytesIO()
    image.save(stream, 'PNG', optimize=False, compress_level=9)
    return stream.getvalue()


def _native(image, palette, threshold):
    """Snap generated pixels to the existing palette without filtered edges."""
    pixels = np.asarray(image.convert('RGBA')).copy()
    opaque = pixels[:, :, 3] >= threshold
    colors = pixels[:, :, :3][opaque].astype(np.int32)
    if len(colors):
        distances = ((colors[:, None, :]-palette[None, :, :])**2).sum(axis=2)
        pixels[:, :, :3][opaque] = palette[distances.argmin(axis=1)]
    pixels[~opaque] = 0
    pixels[:, :, 3][opaque] = 255
    return Image.fromarray(pixels)


def _slice(image, top, bottom):
    layer = Image.new('RGBA', image.size)
    layer.paste(image.crop((0, top, image.width, bottom)), (0, top))
    return layer


def products(source=SOURCE, target=TARGET):
    source, target = Path(source), Path(target)
    recipe = json.loads((source/'recipe.json').read_text())
    for filename, record in recipe['sources'].items():
        if sha256((source/filename).read_bytes()).hexdigest() != record['sha256']:
            raise ValueError(f'Bridge source changed without a recipe update: {filename}')
    size = tuple(recipe['canvas'])
    if size != (288, 144) or recipe['anchor'] != [144, 94]:
        raise ValueError('Bridge artwork must retain its native registration')
    destroyed = Image.open(source/recipe['palette_reference']).convert('RGBA')
    if destroyed.size != size:
        raise ValueError('Destroyed bridge reference has the wrong canvas')
    pixels = np.asarray(destroyed)
    palette = np.unique(pixels[:, :, :3][pixels[:, :, 3] == 255], axis=0).astype(np.int32)
    if len(palette) != recipe['palette_colors']:
        raise ValueError('Bridge palette differs from the preserved native art')
    generated = Image.open(source/'intact_generated.png').convert('RGBA')
    intact = {}
    for layer, band in recipe['intact_bands'].items():
        left, top, right, bottom = band['target_rect']
        crop = generated.crop(tuple(band['source_rect']))
        crop = crop.resize((right-left, bottom-top), Image.Resampling.NEAREST)
        image = Image.new('RGBA', size)
        image.paste(_native(crop, palette, recipe['alpha_threshold']), (left, top))
        intact[layer] = image
    gap_left, gap_right = recipe['destroyed_gap_px']
    destroyed.paste((0, 0, 0, 0), (gap_left, 0, gap_right, size[1]))
    layers = {
        'intact': intact,
        'destroyed': {
            'deck': _slice(destroyed, recipe['deck_top_px'], recipe['deck_bottom_px']),
            'far': _slice(destroyed, 0, recipe['deck_top_px']),
            'near': _slice(destroyed, recipe['deck_bottom_px'], size[1]),
        },
        'restored': {name: image.copy() for name, image in intact.items()},
    }
    output = {}
    manifest = {'version': 1, 'canvas': list(size), 'anchor': recipe['anchor'],
                'deck_top_px': recipe['deck_top_px'],
                'deck_bottom_px': recipe['deck_bottom_px'], 'phases': {}}
    for phase in PHASES:
        manifest['phases'][phase] = {}
        for name in ('deck', 'far', 'near'):
            filename = target/phase/(name+'.png')
            output[filename] = _png(layers[phase][name])
            # Manifest paths are rooted at the repository, independent of an
            # alternate export directory used for reproduction checks.
            relative = TARGET.relative_to(ROOT)/phase/(name+'.png')
            record = {'image': relative.as_posix(), 'foot_anchor': recipe['anchor']}
            if name != 'deck':
                record['sort_offset'] = -60 if name == 'far' else 14
            manifest['phases'][phase][name] = record
    output[target/'art.json'] = (json.dumps(manifest, indent=2)+'\n').encode()
    return output


def build(check=False):
    output = products()
    changed = [path for path, data in output.items()
               if not path.exists() or path.read_bytes() != data]
    if check and changed:
        raise SystemExit('Stale western bridge exports: '+', '.join(
            path.relative_to(ROOT).as_posix() for path in changed))
    if not check:
        for path, data in output.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    build(check=parser.parse_args().check)
