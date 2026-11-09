"""Compile Vespermaw's retained authored atlases into registered pixel poses.

This exporter extracts complete connected silhouettes, applies one shared
opaque-only palette and one fixed nearest-neighbor native scale, and registers
the authored anatomy to an explicit floor. It never draws or synthesizes poses.
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
SOURCE = ROOT/'assets/source/combat/vespermaw'
OUTPUT = ROOT/'assets/combat/vespermaw'
RECIPE = SOURCE/'registration.json'


def encoded(image):
    stream = BytesIO()
    image.save(stream, format='PNG', optimize=True)
    return stream.getvalue()


def split_time(total, count):
    """Distribute integer milliseconds without introducing repeated hold frames."""
    if type(total) is not int or type(count) is not int or not 0 < count <= total:
        raise ValueError('Animation time must contain at least one millisecond per pose')
    return [round((index+1)*total/count)-round(index*total/count)
            for index in range(count)]


def body_alpha(image):
    """Select the whole connected authored animal, excluding low-alpha matte."""
    surface = pygame.image.frombytes(image.tobytes(), image.size, 'RGBA')
    mask = pygame.mask.from_surface(surface, 127).connected_component()
    if mask.count() < 1000:
        raise ValueError('Missing complete Vespermaw body')
    coverage = mask.to_surface(setcolor=(255, 255, 255, 255),
                               unsetcolor=(0, 0, 0, 0))
    return Image.frombytes('RGBA', image.size,
                           pygame.image.tobytes(coverage, 'RGBA')).getchannel('A')


def whole_drawings(path, grid=(8, 4)):
    """Locate whole atlas bodies, including anatomy crossing nominal cells.

    The image generator's grid is an organizational guide, not a cutting mask.
    Returned rectangles support explicit source-space foot/anchor registration.
    """
    surface = pygame.image.load(str(path))
    width, height = surface.get_size()
    columns, rows = grid
    found = {}
    for component in pygame.mask.from_surface(surface, 127).connected_components():
        if component.count() < 1000:continue
        bounds = component.get_bounding_rects()[0]
        column = min(columns-1, max(0, int(bounds.centerx/(width/columns))))
        row = min(rows-1, max(0, int(bounds.centery/(height/rows))))
        index = row*columns+column
        if index in found:
            raise ValueError('Two complete Vespermaw bodies in source cell: '+str(path)+':'+str(index))
        found[index] = list(bounds)
    if set(found) != set(range(columns*rows)):
        raise ValueError('Vespermaw atlas needs '+str(columns*rows)+' isolated complete drawings: '+str(path))
    return found


def products():
    spec = json.loads(RECIPE.read_text(encoding='utf-8'))
    canvas, anchor, scale = spec['canvas'], spec['anchor'], spec['native_scale']
    source_images, source_bodies, colors = {}, {}, []
    for name, expected in spec['source_sha256'].items():
        path = ROOT/name
        if sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Vespermaw source changed: '+name)
        with Image.open(path) as image:source_images[name] = image.convert('RGBA')
        source_bodies[name] = whole_drawings(path, spec['source_grid'])
        colors.extend(pixel[:3] for pixel in source_images[name].get_flattened_data() if pixel[3] >= 128)
    opaque = Image.new('RGB', (len(colors), 1))
    opaque.putdata(colors)
    palette = opaque.quantize(colors=spec['palette_colors'], dither=Image.Dither.NONE)
    drawings, provenance = [], []
    for index, drawing in enumerate(spec['drawings']):
        source = source_images[drawing['source_sheet']]
        left, top, width, height = drawing['source_rect']
        if not (0 <= left < left+width <= source.width
                and 0 <= top < top+height <= source.height):
            raise ValueError('Invalid Vespermaw source bounds: '+str(index))
        whole = source_bodies[drawing['source_sheet']][drawing['source_cell']]
        if not (left <= whole[0] and top <= whole[1]
                and left+width >= whole[0]+whole[2] and top+height >= whole[1]+whole[3]):
            raise ValueError('Registration clips authored Vespermaw anatomy: '+str(index))
        body = source.crop((left, top, left+width, top+height))
        body.putalpha(body_alpha(body))
        body = body.resize((max(1, round(width*scale)), max(1, round(height*scale))),
                           Image.Resampling.NEAREST)
        alpha = body.getchannel('A')
        body = body.convert('RGB').quantize(palette=palette,
                       dither=Image.Dither.NONE).convert('RGBA')
        body.putalpha(alpha)
        foot = drawing['source_foot']
        position = [round(anchor[0]-(foot[0]-left)*scale),
                    round(anchor[1]-(foot[1]-top)*scale)]
        frame = Image.new('RGBA', tuple(canvas))
        frame.alpha_composite(body, tuple(position))
        bounds = frame.getbbox()
        if (bounds is None or bounds[0] <= 0 or bounds[1] <= 0
                or bounds[2] >= canvas[0] or bounds[3] >= canvas[1]):
            raise ValueError('Clipped Vespermaw pose: '+str(index))
        if set(frame.getchannel('A').tobytes())-{0, 255}:
            raise ValueError('Vespermaw alpha must be binary')
        anchors = {'floor': list(anchor)}
        for key, point in drawing['source_anchors'].items():
            anchors[key] = [round(anchor[0]+(point[0]-foot[0])*scale),
                            round(anchor[1]+(point[1]-foot[1])*scale)]
        if not {'floor', 'body', 'contact', 'cast_origin'} <= set(anchors):
            raise ValueError('Missing Vespermaw anatomical anchors')
        drawings.append(frame)
        provenance.append({**drawing,
            'source_sha256': spec['source_sha256'][drawing['source_sheet']],
            'native_scale': scale, 'native_bounds': list(bounds),
            'position': position, 'anchors': anchors})

    result, animations, sheet_frames = {}, {}, []
    used = []
    for state, animation_spec in spec['animations'].items():
        indices = animation_spec['drawings']
        count = len(indices)
        contact = animation_spec.get('contact_frame')
        if contact is None:
            durations = split_time(animation_spec['duration_ms'], count)
        else:
            durations = (split_time(animation_spec['contact_ms'], contact)
                         +split_time(animation_spec['duration_ms']-animation_spec['contact_ms'],
                                     count-contact))
        frames = []
        fingerprints = set()
        for number, (index, duration) in enumerate(zip(indices, durations), 1):
            frame = drawings[index]
            name = f'{state}_{number:02}.png'
            result[(OUTPUT/name).relative_to(ROOT).as_posix()] = encoded(frame)
            frames.append({**provenance[index], 'file': name, 'duration_ms': duration})
            fingerprints.add(sha256(frame.tobytes()).digest())
            sheet_frames.append(frame)
            used.append(index)
        if len(fingerprints) < count*.9:
            raise ValueError('Repeated Vespermaw poses cannot inflate an animation: '+state)
        animations[state] = {'loop': animation_spec['loop'], 'frames': frames}
        for field in ('contact_frame', 'contact_ms'):
            if field in animation_spec:animations[state][field] = animation_spec[field]
    if sorted(used) != list(range(len(drawings))):
        raise ValueError('Each authored Vespermaw drawing must be used exactly once')
    columns = 16
    rows = (len(sheet_frames)+columns-1)//columns
    sheet = Image.new('RGBA', (columns*canvas[0], rows*canvas[1]))
    for index, frame in enumerate(sheet_frames):
        sheet.alpha_composite(frame, ((index%columns)*canvas[0], (index//columns)*canvas[1]))
    result[(OUTPUT/'spritesheet.png').relative_to(ROOT).as_posix()] = encoded(sheet)
    manifest = {'version': 1, 'actor': 'vespermaw', 'canvas': canvas, 'anchor': anchor,
                'facing': 'right', 'sheet': 'spritesheet.png',
                'authored_frames': len(drawings), 'source_grid': spec['source_grid'],
                'source_sha256': spec['source_sha256'],
                'registration': RECIPE.relative_to(ROOT).as_posix(),
                'registration_sha256': sha256(RECIPE.read_bytes()).hexdigest(),
                'native_scale': scale, 'palette_colors': spec['palette_colors'],
                'extraction': 'complete connected authored bodies; binary alpha; shared opaque-only palette; fixed nearest-neighbor scale; explicit anatomical floor and per-frame contact/cast anchors',
                'animations': animations}
    result[(OUTPUT/'animation.json').relative_to(ROOT).as_posix()] = (
        json.dumps(manifest, indent=2)+'\n').encode()
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    output = products()
    changed = []
    for name, content in output.items():
        path = ROOT/name
        if not path.exists() or path.read_bytes() != content:
            changed.append(name)
            if not args.check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
    if args.check and changed:
        raise SystemExit('Stale Vespermaw combat exports: '+', '.join(changed))
    print(('Verified' if args.check else 'Built')
          +f' {len(output)-2} authored Vespermaw poses / {len(output)} exports')
    return 0


if __name__ == '__main__':raise SystemExit(main())
