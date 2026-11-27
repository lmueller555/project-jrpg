"""Export registered complete frozen figures and their clean bridge backdrop.

Only authored silhouette alpha/canvas registration changes: the approved
character pixels are preserved, with no limb construction or pose warping.
The background reconstruction is retained separately from the generated art.
"""
from __future__ import annotations

import argparse
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/cinematics/fire_veinhold/continuation/materials'
POLYGONS = {
    'left_back':[(172,200),(205,243),(220,286),(215,402),(174,414),
                 (97,411),(98,370),(108,300),(114,251),(134,218)],
    'left_front':[(296,148),(357,208),(388,295),(414,403),(429,530),
                  (386,558),(155,559),(144,523),(155,436),(174,354),
                  (195,279),(221,221),(259,170)],
    'right_mid':[(735,196),(778,224),(796,282),(811,353),(816,435),
                 (794,461),(613,461),(600,432),(615,369),(637,306),
                 (668,248),(698,219)],
    'right_back':[(867,204),(901,225),(919,281),(930,369),(913,401),
                  (787,399),(781,357),(796,290),(824,239)],
}


def _png(image):
    stream = BytesIO()
    image.save(stream, 'PNG', compress_level=6)
    return stream.getvalue()


def products(folder=SOURCE):
    folder = Path(folder)
    original = Image.open(folder/'frozen_bridge_final.png').convert('RGBA')
    empty = Image.open(folder/'frozen_bridge_empty_generated.png').convert('RGBA')
    if original.size != (1536,1024) or empty.size != original.size:
        raise ValueError('Frozen bridge sources must retain their common 1536×1024 canvas')
    masks = {}
    for name, polygon in POLYGONS.items():
        mask = Image.new('L', original.size)
        ImageDraw.Draw(mask).polygon([(round(x*1.6), round(y*1.6)) for x,y in polygon], fill=255)
        masks[name] = mask.filter(ImageFilter.MaxFilter(7))
    # The nearer complete figure owns the overlap. Do not copy its hand or
    # crystal onto the rear figure's otherwise visible source silhouette.
    masks['left_back'] = ImageChops.subtract(masks['left_back'], masks['left_front'])
    masks['right_back'] = ImageChops.subtract(masks['right_back'], masks['right_mid'])
    union = Image.new('L', original.size)
    result, layers, records = {}, {}, []
    for name, polygon in POLYGONS.items():
        mask = masks[name]
        union = ImageChops.lighter(union, mask)
        layer = original.copy()
        layer.putalpha(mask)
        filename = f'frozen_guard_{name}.png'
        result[folder/filename] = _png(layer)
        layers[name] = layer
        records.append({'id':name, 'file':filename, 'canvas':list(original.size),
                        'alpha_bounds':list(mask.getbbox()), 'polygon_at_960x640':polygon})
    background = Image.composite(empty, original, union)
    result[folder/'frozen_bridge_background.png'] = _png(background)
    reconstructed = background.copy()
    for name in ('left_back','right_back','right_mid','left_front'):
        reconstructed = Image.alpha_composite(reconstructed, layers[name])
    if ImageChops.difference(reconstructed, original).convert('RGB').getbbox() is not None:
        raise ValueError('Frozen layers no longer reconstruct the approved painting exactly')
    data = {'version':1, 'source':'frozen_bridge_final.png',
            'background':'frozen_bridge_background.png',
            'background_generated':'frozen_bridge_empty_generated.png',
            'alpha_method':'Authored ice-silhouette polygons with three-source-pixel safety dilation. '
                'Original pixels and source-visible rear-body regions are preserved; no anatomy or limb manipulation.',
            'flat_reconstruction':'Pixel-exact RGB reconstruction of the approved complete painting.',
            'guards':records}
    result[folder/'frozen_guard_layers.json'] = (json.dumps(data,indent=2)+'\n').encode()
    return result


def build(check=False):
    output = products()
    stale = [path.name for path, data in output.items() if not path.exists() or path.read_bytes() != data]
    if check and stale:
        raise ValueError('Stale frozen guard exports: '+', '.join(stale))
    if not check:
        for path, data in output.items():path.write_bytes(data)
    print('Four complete frozen figure layers and bridge background reproduce exactly.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    build(parser.parse_args().check)
