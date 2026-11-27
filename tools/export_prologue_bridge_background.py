"""Export registered far scenery and a transparent lateral steel bridge."""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/cinematics/fire_veinhold/bridge_running/environment'
OUTPUT = ROOT/'assets/story/fire_veinhold_opening/shot06/environment'
LAYERS = (
    ('far', 'far_generated.png', 'RGB', 'far_prompt.txt',
     '/workspace/generated_images/exec-ab894625-d4ea-449b-bcb1-10a0f5518e38.png'),
    ('bridge', 'bridge_generated.png', 'RGBA', 'bridge_prompt.txt',
     '/workspace/generated_images/exec-21db1215-b501-4b6f-85a1-ac5084553ca2.png'),
)


def export(check=False):
    records, outputs = [], {}
    for name, filename, mode, prompt, generation_path in LAYERS:
        master = SOURCE/filename
        image = Image.open(master).convert(mode)
        source_size = list(image.size)
        if image.width != image.height*3:
            raise ValueError('Lateral layers must retain their shared 3:1 composition')
        if mode == 'RGBA':
            alpha = image.getchannel('A')
            if alpha.getextrema() != (0, 255):
                raise ValueError('The bridge overlay requires genuine transparent gaps')
            transparent = alpha.histogram()[0]/(image.width*image.height)
            if not .15 < transparent < .65:
                raise ValueError('Unexpected transparent bridge silhouette')
            # The background-removal export contains isolated alpha=1 specks
            # in otherwise empty sky. Remove only that quantization dust.
            image.putalpha(alpha.point(lambda value:0 if value <= 1 else value))
        # Uniform whole-canvas sampling retains source coordinates and alpha;
        # no scenery is painted or segmented by the technical exporter.
        image = image.resize((1920, 640), Image.Resampling.LANCZOS)
        if mode == 'RGBA':
            image.putalpha(image.getchannel('A').point(lambda value:0 if value <= 1 else value))
        data = BytesIO();image.save(data, format='PNG', optimize=True)
        expected = data.getvalue()
        output = OUTPUT/f'{name}.png'
        outputs[output] = expected
        records.append({'id':name, 'generator':'image_gen',
            'generation_path':generation_path, 'source':filename,
            'source_sha256':sha256(master.read_bytes()).hexdigest(), 'prompt':prompt,
            'source_size':source_size, 'export_size':[1920, 640], 'mode':mode,
            'output':output.relative_to(ROOT).as_posix(),
            'output_sha256':sha256(expected).hexdigest()})
    reference = SOURCE/'background_generated.png'
    recipe = {'version':2, 'layers':records,
        'reference':{'source':reference.name,
            'source_sha256':sha256(reference.read_bytes()).hexdigest(),
            'generation_path':'/workspace/generated_images/exec-610f83a4-3470-44c3-96c2-d2e59d944b2c.png',
            'prompt':'prompt.txt', 'status':'Whole-scene design reference; not runtime artwork.'},
        'operation':'Uniform whole-layer Lanczos resize; preserve authored bridge alpha '
                    'above the alpha<=1 quantization-dust threshold.',
        'staging':'Far sky/sea/mountains stay fixed over this short side-on camera translation. '
                  'The complete rail/deck overlay moves at ground speed in both modes. '
                  'Runtime alternates mirrored repeat tiles to share exact edge pixels.'}
    recipe_path = SOURCE/'recipe.json'
    obsolete = OUTPUT/'background.png'
    if check:
        for output, expected in outputs.items():
            if output.read_bytes() != expected:
                raise ValueError('A lateral layer differs from its authored source')
        if json.loads(recipe_path.read_text()) != recipe or obsolete.exists():
            raise ValueError('Lateral layer recipe or retired combined painting is inconsistent')
        print('Far scenery and transparent bridge reproduce exactly at 1920x640.')
    else:
        OUTPUT.mkdir(parents=True, exist_ok=True)
        for output, expected in outputs.items():output.write_bytes(expected)
        recipe_path.write_text(json.dumps(recipe, indent=2)+'\n')
        obsolete.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    export(parser.parse_args().check)
