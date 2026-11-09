"""Extract Veylume's authored atlases into registered native combat poses.

The five imagegen originals are retained unchanged. Extraction selects each
whole connected alpha silhouette, preserving wing tips beyond nominal grid
lines; one fixed nearest-neighbor scale, opaque-only shared palette and binary
coverage provide crisp native pixels. No pose is redrawn, warped or synthesized.
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
SOURCE = ROOT/'assets/source/combat/veylume'
OUTPUT = ROOT/'assets/combat/veylume'
RECIPE = SOURCE/'registration.json'


def encoded(image):
    data = BytesIO()
    image.save(data, format='PNG', optimize=True)
    return data.getvalue()


def durations(total, count):
    """Integer milliseconds with exact total and no artificial held copies."""
    return [round((index+1)*total/count)-round(index*total/count)
            for index in range(count)]


def whole_drawings(path):
    """Find complete bodies on the whole atlas, never a clipping grid crop."""
    surface = pygame.image.load(str(path))
    mask = pygame.mask.from_surface(surface, 127)
    width, height = surface.get_size()
    found = {}
    # Apply the area filter in Python: SDL/Pygame's optional min argument can
    # omit a valid thin-winged component despite its actual count exceeding it.
    for component in mask.connected_components():
        if component.count() < 4000:continue
        bounds = component.get_bounding_rects()[0]
        column = min(7, max(0, int(bounds.centerx/(width/8))))
        row = min(3, max(0, int(bounds.centery/(height/4))))
        index = row*8+column
        if index in found:
            raise ValueError('Two complete Veylume bodies in one cell: '+str(path)+':'+str(index))
        local = pygame.Mask(bounds.size)
        local.draw(component, (-bounds.x, -bounds.y))
        alpha_surface = local.to_surface(setcolor=(255,255,255,255), unsetcolor=(0,0,0,0))
        alpha = Image.frombytes('RGBA', bounds.size, pygame.image.tobytes(alpha_surface, 'RGBA')).getchannel('A')
        image = Image.frombytes('RGBA', bounds.size,
                                pygame.image.tobytes(surface.subsurface(bounds), 'RGBA'))
        image.putalpha(alpha)
        rect = list(bounds)
        found[index] = {'image': image, 'rect': rect,
                        'pivot': [(column+.5)*width/8, (row+1)*height/4]}
    if set(found) != set(range(32)):
        raise ValueError('Veylume atlas needs 32 isolated complete drawings: '+str(path))
    return found


def products():
    recipe = json.loads(RECIPE.read_text())
    canvas, anchor, scale = recipe['canvas'], recipe['anchor'], recipe['native_scale']
    atlases = {name: whole_drawings(SOURCE/name) for name in recipe['atlases']}
    source_hashes = {(SOURCE/name).relative_to(ROOT).as_posix(): sha256((SOURCE/name).read_bytes()).hexdigest()
                     for name in recipe['atlases']}
    # A single palette is derived exclusively from opaque body pixels. The
    # low-alpha colored matte outside the originals' drawings cannot affect it.
    colors = []
    for drawings in atlases.values():
        for record in drawings.values():
            colors.extend(pixel[:3] for pixel in record['image'].getdata() if pixel[3])
    opaque = Image.new('RGB', (len(colors), 1))
    opaque.putdata(colors)
    palette = opaque.quantize(colors=recipe['palette_colors'], dither=Image.Dither.NONE)
    out, animations, all_frames = {}, {}, []
    for state, specification in recipe['animations'].items():
        selections = [(name, cell) for part in specification['sources']
                      for name, cells in [part] for cell in cells]
        count = len(selections)
        contact_frame = specification.get('contact_frame')
        if contact_frame is None:
            timing = durations(specification['duration_ms'], count)
        else:
            timing = (durations(specification['contact_ms'], contact_frame)
                      +durations(specification['duration_ms']-specification['contact_ms'], count-contact_frame))
        records, unique = [], set()
        for index, ((name, cell), duration) in enumerate(zip(selections, timing)):
            drawing = atlases[name][cell]
            cutout = drawing['image']
            x, y, width, height = drawing['rect']
            pivot = list(drawing['pivot'])
            # The last collapsed poses have an authored floor contact rather
            # than a hovering pivot; keep their actual supporting pixels down.
            if state == 'defeat' and index >= count-4:
                pivot[1] = y+height
            image = cutout.resize((max(1, round(width*scale)), max(1, round(height*scale))),
                                   Image.Resampling.NEAREST)
            alpha = image.getchannel('A')
            image = image.convert('RGB').quantize(palette=palette,
                         dither=Image.Dither.NONE).convert('RGBA')
            image.putalpha(alpha)
            position = [round(anchor[0]-(pivot[0]-x)*scale),
                        round(anchor[1]-(pivot[1]-y)*scale)]
            frame = Image.new('RGBA', canvas)
            frame.alpha_composite(image, tuple(position))
            bounds = frame.getbbox()
            if bounds is None or bounds[0] <= 0 or bounds[1] <= 0 or bounds[2] >= canvas[0] or bounds[3] >= canvas[1]:
                raise ValueError('Clipped Veylume pose: '+state+':'+str(index))
            fingerprint = sha256(frame.tobytes()).hexdigest()
            if fingerprint in unique:
                raise ValueError('Repeated Veylume drawing: '+state+':'+str(index))
            unique.add(fingerprint)
            filename = f'{state}_{index+1:02}.png'
            out[(OUTPUT/filename).relative_to(ROOT).as_posix()] = encoded(frame)
            path = (SOURCE/name).relative_to(ROOT).as_posix()
            records.append({'file': filename, 'duration_ms': duration,
                            'source_sheet': path, 'source_cell': cell,
                            'source_rect': drawing['rect'], 'source_pivot': pivot,
                            'source_sha256': source_hashes[path],
                            'native_scale': scale, 'position': position,
                            'anchors': {'floor': anchor, 'cast_origin': [80,38], 'body': [56,65]}})
            all_frames.append(frame)
        animation = {'loop': specification['loop'], 'frames': records}
        for field in ('contact_ms', 'contact_frame'):
            if field in specification:animation[field] = specification[field]
        animations[state] = animation
    columns = 16
    rows = (len(all_frames)+columns-1)//columns
    sheet = Image.new('RGBA', (columns*canvas[0], rows*canvas[1]))
    for index, frame in enumerate(all_frames):
        sheet.alpha_composite(frame, ((index%columns)*canvas[0], (index//columns)*canvas[1]))
    out[(OUTPUT/'spritesheet.png').relative_to(ROOT).as_posix()] = encoded(sheet)
    manifest = {'version': 1, 'actor': 'veylume', 'canvas': canvas, 'anchor': anchor,
                'facing': 'right', 'sheet': 'spritesheet.png', 'source_grid': [8,4],
                'source_sheets': list(source_hashes), 'source_sha256': source_hashes,
                'registration': RECIPE.relative_to(ROOT).as_posix(),
                'registration_sha256': sha256(RECIPE.read_bytes()).hexdigest(),
                'authored_frames': len(all_frames), 'native_scale': scale,
                'extraction': 'whole-atlas connected alpha silhouettes; fixed nearest-neighbor native scale; binary alpha; shared opaque-only palette; fixed cell pivot and explicit corpse floor contact',
                'animations': animations}
    out[(OUTPUT/'animation.json').relative_to(ROOT).as_posix()] = (json.dumps(manifest, indent=2)+'\n').encode()
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    result = products()
    changed = []
    for name, raw in result.items():
        path = ROOT/name
        if not path.exists() or path.read_bytes() != raw:
            changed.append(name)
            if not args.check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
    if args.check and changed:
        raise SystemExit('Stale Veylume combat exports: '+', '.join(changed))
    print(('Verified' if args.check else 'Built')+' 160 authored Veylume combat poses')
    return 0


if __name__ == '__main__':raise SystemExit(main())
