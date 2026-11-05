"""Register authored panoramic scenery and transparent fixed-world landmarks.

Generated sources are retained untouched. Registration is nearest-neighbour
scaling, alpha cleanup, landmark trimming and a narrow periodic edge join.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/cinematics/ice_reaper_continuity/environment'
OUTPUT = ROOT/'assets/story/ice_reaper_continuity/environment'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    panorama_source = SOURCE/'panorama_generated.png'
    landmark_source = SOURCE/'landmarks_generated.png'
    panorama = Image.open(panorama_source).convert('RGB').resize(
        (3072, 768), Image.Resampling.NEAREST)
    pixels = np.asarray(panorama).astype(np.float32).copy()
    # Join the periodic texture boundary without mirroring the world or
    # duplicating its features. Only the outer 64 columns on each side change.
    width = pixels.shape[1]
    join_width = 64
    for offset in range(join_width):
        left = pixels[:, offset].copy()
        right = pixels[:, width-1-offset].copy()
        average = (left+right)*.5
        weight = (1-offset/(join_width-1))**2
        pixels[:, offset] = left*(1-weight)+average*weight
        pixels[:, width-1-offset] = right*(1-weight)+average*weight
    panorama = Image.fromarray(np.rint(pixels).astype(np.uint8))
    panorama.save(OUTPUT/'panorama.png', optimize=True)

    sheet = Image.open(landmark_source).convert('RGBA')
    # Authored groups have transparent gutters; these are registration cells,
    # not newly drawn or rearranged architecture.
    cells = {'castle': (0, 0, 790, 724),
             'forest': (790, 0, 1435, 724),
             'ruins': (1435, 0, 2172, 724)}
    landmarks = {}
    for name, cell in cells.items():
        image = sheet.crop(cell)
        image.putalpha(image.getchannel('A').point(lambda a: 0 if a < 40 else a))
        bounds = image.getbbox()
        if bounds is None:
            raise ValueError(f'Empty authored landmark: {name}')
        image = image.crop(bounds)
        scale = 512/image.height
        image = image.resize((round(image.width*scale), 512), Image.Resampling.NEAREST)
        image.save(OUTPUT/f'{name}.png', optimize=True)
        landmarks[name] = {
            'file': f'{name}.png', 'canvas': list(image.size),
            'anchor': [image.width//2, image.height-1],
            'source_cell': list(cell), 'trim_bounds': list(bounds),
        }
    metadata = {
        'version': 1,
        'panorama': {
            'file': 'panorama.png', 'canvas': [3072, 768],
            'horizontal_degrees': 360, 'horizon_y': .66,
            'cloud_horizon_y': .54,
            'above_horizon_degrees': 80, 'below_horizon_degrees': 40,
            'seam_join_columns': join_width,
            'contains_castle': False,
        },
        'landmarks': landmarks,
        'sources': [{'file': str(path.relative_to(ROOT)), 'sha256': sha256(path)}
                    for path in (panorama_source, landmark_source)],
        'operations': [
            'Image-generated panorama and isolated landmark atlas use approved scenery references.',
            'Generated source PNGs retained unchanged.',
            'Nearest-neighbour panorama registration to 3072x768.',
            'Symmetric 64-column overlap edge blend makes the panorama periodic.',
            'Landmark transparent-cell crop, alpha threshold 40 and nearest registration to 512px height.',
            'No landmarks are baked into the panoramic sky and mountain texture.',
        ],
        'review_status': 'awaiting_user_review',
    }
    (OUTPUT/'manifest.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print('Registered 3072x768 periodic panorama and castle/forest/ruins landmark sprites.')


if __name__ == '__main__':
    build()
