"""Extract Lithrusk's 96 authored imagegen poses at one native pixel scale.

The three retained source atlases are unchanged generated art. Registration
selects each complete connected body, including pincers that cross a nominal
grid boundary. Extraction performs binary-alpha cleanup, shared-palette color
registration and fixed nearest-neighbor scaling only; it creates no new poses.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
from PIL import Image
import pygame


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/combat/lithrusk'
OUTPUT = ROOT/'assets/combat/lithrusk'


def split_time(total, count):
    base, remainder = divmod(total, count)
    return [base+(index < remainder) for index in range(count)]


ANIMATIONS = {
    'idle': (range(0, 16), [100]*16, True),
    'walk': (range(16, 32), [70]*16, True),
    'claw_clamp': (range(32, 48), split_time(400, 8)+split_time(400, 8), False),
    'shell_bash': (range(48, 64), split_time(500, 8)+split_time(450, 8), False),
    'hurt': (range(64, 80), split_time(500, 16), False),
    'defeat': (range(80, 96), split_time(1000, 16), False),
}
CONTACT = {'claw_clamp': 400, 'shell_bash': 500}


def encoded(image):
    stream = BytesIO()
    image.save(stream, format='PNG', optimize=True)
    return stream.getvalue()


def body_alpha(image):
    """Retain the connected authored body, excluding low-alpha matte residue."""
    surface = pygame.image.frombytes(image.tobytes(), image.size, 'RGBA')
    mask = pygame.mask.from_surface(surface, 127).connected_component()
    if mask.count() < 1000:
        raise ValueError('Missing complete Lithrusk drawing')
    coverage = mask.to_surface(setcolor=(255, 255, 255, 255),
                               unsetcolor=(0, 0, 0, 0))
    return Image.frombytes('RGBA', image.size,
                           pygame.image.tobytes(coverage, 'RGBA')).getchannel('A')


def products():
    registration = SOURCE/'registration.json'
    spec = json.loads(registration.read_text())
    source_images = {}
    visible = []
    for name, expected in spec['source_sha256'].items():
        path = ROOT/name
        if sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Lithrusk source changed: '+name)
        with Image.open(path) as image:
            source_images[name] = image.convert('RGBA')
        pixels = iter(source_images[name].tobytes())
        visible.extend((red, green, blue) for red, green, blue, alpha
                       in zip(pixels, pixels, pixels, pixels) if alpha >= 128)
    colors = Image.new('RGB', (len(visible), 1))
    colors.putdata(visible)
    palette = colors.quantize(colors=spec['palette_colors'], dither=Image.Dither.NONE)
    canvas, anchor = spec['canvas'], spec['anchor']
    scale = spec['native_scale']
    drawings, records = [], []
    for drawing in spec['drawings']:
        left, top, width, height = drawing['source_rect']
        source = source_images[drawing['source_sheet']]
        body = source.crop((left, top, left+width, top+height))
        body.putalpha(body_alpha(body))
        body = body.resize((round(width*scale), round(height*scale)), Image.Resampling.NEAREST)
        alpha = body.getchannel('A')
        body = body.convert('RGB').quantize(palette=palette,
                    dither=Image.Dither.NONE).convert('RGBA')
        body.putalpha(alpha)
        foot = drawing['source_foot']
        position = [round(anchor[0]-(foot[0]-left)*scale),
                    round(anchor[1]-(foot[1]-top)*scale)]
        image = Image.new('RGBA', canvas)
        image.alpha_composite(body, tuple(position))
        bounds = image.getbbox()
        if (bounds is None or bounds[0] <= 0 or bounds[1] <= 0
                or bounds[2] >= canvas[0] or bounds[3] >= canvas[1]):
            raise ValueError('Clipped Lithrusk pose: '+str(drawing))
        if set(image.getchannel('A').tobytes())-{0, 255}:
            raise ValueError('Lithrusk alpha must be binary')
        drawings.append(image)
        records.append({**drawing, 'source_sha256': spec['source_sha256'][drawing['source_sheet']],
                        'native_scale': scale, 'native_bounds': list(bounds),
                        'anchors': {'floor': anchor, 'body': [48, 64],
                                    'contact': [bounds[2]-2, 69]}})
    if len(drawings) != 96 or len({image.tobytes() for image in drawings}) != 96:
        raise ValueError('Lithrusk requires 96 distinct authored drawings')
    result, animations = {}, {}
    def emit(name, image):
        result[(OUTPUT/name).relative_to(ROOT).as_posix()] = encoded(image)
    for state, (indices, timings, loop) in ANIMATIONS.items():
        frames = []
        for number, (index, duration) in enumerate(zip(indices, timings), 1):
            name = f'{state}_{number:02}.png'
            emit(name, drawings[index])
            frames.append({**records[index], 'file': name, 'duration_ms': duration})
        animation = {'loop': loop, 'frames': frames}
        if state in CONTACT:
            animation.update(contact_ms=CONTACT[state], contact_frame=8)
        animations[state] = animation
    sheet = Image.new('RGBA', (canvas[0]*8, canvas[1]*12))
    for index, image in enumerate(drawings):
        sheet.alpha_composite(image, ((index % 8)*canvas[0], (index//8)*canvas[1]))
    emit('spritesheet.png', sheet)
    metadata = {'version': 1, 'actor': 'lithrusk', 'canvas': canvas, 'anchor': anchor,
                'facing': 'right', 'sheet': 'spritesheet.png', 'authored_frames': 96,
                'source_grid': [8, 4], 'source_sha256': spec['source_sha256'],
                'registration': registration.relative_to(ROOT).as_posix(),
                'registration_sha256': sha256(registration.read_bytes()).hexdigest(),
                'native_scale': scale, 'palette_colors': spec['palette_colors'],
                'extraction': 'complete connected authored body; binary alpha; shared palette; fixed nearest-neighbor scale; explicit anatomical floor',
                'animations': animations}
    result[(OUTPUT/'animation.json').relative_to(ROOT).as_posix()] = (
        json.dumps(metadata, indent=2)+'\n').encode()
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    result = products()
    changed = []
    for name, content in result.items():
        path = ROOT/name
        if not path.exists() or path.read_bytes() != content:
            changed.append(name)
            if not args.check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
    if args.check and changed:
        raise SystemExit('Stale Lithrusk exports: '+', '.join(changed))
    print(('Verified' if args.check else 'Built')+f' {len(result)} Lithrusk exports / 96 authored poses')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
