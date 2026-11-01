#!/usr/bin/env python3
"""Build hand-authored native wildlife pixels and their registered clip API.

Every contour, fleece cluster, feather and limb is authored on its final pixel
canvas. No generated rescale, frame interpolation, body warp or runtime drawing.
The original decorative animals are read only for provenance and palette checks.
Run `python tools/build_regional_wildlife.py --check` to check committed exports.
"""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/characters/regional_wildlife'
SOURCE = ROOT / 'assets/source/characters/regional_wildlife'
ORIGINAL = ROOT / 'assets/terrain/overworld/elden_vale/polish/props'
FAMILIES = {
    'sheep': {'size': [24, 20], 'anchor': [12, 18]},
    'cat': {'size': [24, 18], 'anchor': [12, 16]},
    'bird': {'size': [12, 12], 'anchor': [6, 10]},
    'butterfly': {'size': [12, 12], 'anchor': [6, 10]},
}
# Warm cream/brown/amber chosen from the six existing Elden Vale animals.
# The cat uses those same earth colors with desaturated slate-brown tabby fur.
PALETTES = {
    'sheep': {'edge': '#4f3d2d', 'deep': '#352d21', 'skin': '#8b6b4d',
              'skinlight': '#b4936e', 'woolshadow': '#ab8b68', 'wooldark': '#c2a079',
              'wool': '#d9b88e', 'woollight': '#f5d9b3', 'cream': '#f8deba',
              'eye': '#0e0b09'},
    'cat': {'edge': '#41352a', 'deep': '#352d21', 'furshadow': '#706052',
            'fur': '#96816b', 'furlight': '#baa084', 'cream': '#d0af85',
            'muzzle': '#edd0a7', 'eye': '#2c291f', 'iris': '#cbaa68',
            'nose': '#99715c'},
    'bird': {'edge': '#402f23', 'deep': '#26150c', 'brown': '#754728',
             'wing': '#966643', 'light': '#b99474', 'cream': '#ddc29c',
             'beak': '#a3896e', 'eye': '#0c0500'},
    'butterfly': {'edge': '#533d25', 'deep': '#211407', 'amber': '#d9ad5a',
                  'gold': '#f1c56d', 'light': '#fcdf95', 'shadow': '#ab7f3d'},
}


def canvas(family):
    im = Image.new('RGBA', tuple(FAMILIES[family]['size']))
    return im, ImageDraw.Draw(im), PALETTES[family]


def poly(d, xy, color):
    d.polygon(xy, fill=color)


def points(d, xy, color):
    d.point(xy, fill=color)


def sheep_leg(d, p, x, toe, far=False):
    """Knee bends move independently; planted toes stay on the ground plane."""
    y = 17 if far else 18
    d.line([(x, 12), (x, 15), (toe, y-1)], fill=p['edge'], width=2)
    d.line([(x, 13), (x, 15)], fill=p['skin'], width=1)
    d.line([(toe-1, y), (toe+1, y)], fill=p['deep'])
    if not far:
        points(d, [(toe, y-1)], p['skinlight'])


def sheep(pose, phase):
    im, d, p = canvas('sheep')
    # Two far and two near legs are separate jointed shapes, never a translated body.
    feet = ((7, 15, 5, 17), (8, 14, 6, 16), (6, 16, 8, 14), (6, 16, 7, 15))
    toes = feet[phase % 4] if pose == 'walk' else (7, 15, 5, 17)
    for x, toe in zip((7, 14), toes[:2]):
        sheep_leg(d, p, x, toe, True)
    # Short raised tail and scalloped fleece contour.
    poly(d, [(2, 9), (0, 8), (1, 6), (3, 7), (4, 10)], p['wooldark'])
    points(d, [(1, 7), (2, 7)], p['woollight'])
    poly(d, [(2, 7), (3, 5), (5, 5), (6, 3), (9, 3), (10, 4),
             (12, 3), (15, 4), (17, 5), (18, 8), (18, 11), (17, 13),
             (15, 14), (12, 14), (11, 15), (8, 14), (5, 14), (3, 12), (2, 10)], p['woolshadow'])
    poly(d, [(3, 7), (4, 5), (7, 4), (9, 4), (10, 5), (12, 4),
             (15, 5), (17, 7), (17, 10), (15, 12), (12, 13), (7, 12), (4, 11)], p['wool'])
    # Scalloped light clusters describe curls without noisy checkerboard shading.
    clusters = [([(4, 6), (7, 5), (9, 5), (9, 7), (7, 8), (4, 8)], 'woollight'),
                ([(10, 5), (12, 4), (14, 5), (14, 7), (11, 8), (10, 7)], 'woollight'),
                ([(4, 9), (6, 8), (8, 9), (7, 11), (5, 11)], 'woollight'),
                ([(9, 9), (11, 8), (13, 9), (12, 11), (10, 12), (9, 11)], 'woollight'),
                ([(14, 8), (16, 7), (17, 8), (16, 10), (14, 11)], 'woollight')]
    for shape, color in clusters:
        poly(d, shape, p[color])
    points(d, [(5, 5), (6, 5), (11, 5), (12, 5), (5, 9), (10, 9), (15, 8)], p['cream'])
    points(d, [(3, 10), (5, 12), (8, 12), (12, 12), (14, 12), (16, 11)], p['wooldark'])
    points(d, [(7, 7), (12, 7), (6, 11), (11, 11)], p['wool'])
    for x, toe in zip((5, 16), toes[2:]):
        sheep_leg(d, p, x, toe)
    # A low neck is tucked behind the head while grazing/nosing; the wool body stays still.
    if pose == 'graze':
        y = 12 + (phase in (1, 2))
        poly(d, [(16, 9), (19, 10), (20, 13), (18, 15), (16, 13)], p['skin'])
        poly(d, [(18, y), (21, y-1), (22, y+1), (23, y+3), (22, y+4), (20, y+4), (18, y+2)], p['edge'])
        poly(d, [(19, y), (21, y), (22, y+2), (21, y+3), (19, y+2)], p['skin'])
        points(d, [(19, y), (20, y)], p['skinlight'])
        points(d, [(21, y+1)], p['eye'])
        d.line([(16, y), (18, y+1)], fill=p['skinlight'])
        muzzle = (22, y+3)
        if phase == 2:
            points(d, [(22, y+4)], p['skinlight'])
    else:
        nuzzle = pose == 'nuzzle'
        hx = 17 + (nuzzle and phase in (1, 2))
        hy = 8 + (nuzzle and phase in (1, 2)) - (pose == 'look' and phase == 2)
        poly(d, [(16, 7), (19, 8), (19, 12), (16, 12)], p['skin'])
        poly(d, [(hx, hy-2), (hx+3, hy-2), (hx+4, hy-1), (hx+4, hy+1),
                 (hx+5, hy+2), (hx+4, hy+3), (hx+1, hy+3), (hx, hy+1)], p['edge'])
        poly(d, [(hx+1, hy-1), (hx+3, hy-1), (hx+3, hy+2), (hx+1, hy+2)], p['skin'])
        points(d, [(hx+1, hy-1), (hx+2, hy-1), (hx+4, hy+2)], p['skinlight'])
        d.line([(hx-2, hy), (hx, hy+1)], fill=p['skinlight'])
        points(d, [(hx+3, hy)], p['eye'])
        if pose == 'look' and phase == 1:
            points(d, [(hx+3, hy)], p['edge'])
        # Forehead fleece joins continuously to the shoulder.
        points(d, [(hx, hy-2), (hx+1, hy-2)], p['woollight'])
        muzzle = (hx+5, hy+2)
    return im, {'muzzle': list(muzzle), 'ground_contacts': [[toes[2], 18], [toes[3], 18]]}


def cat_head(d, p, x, y, closed=False, lowered=False):
    # Seven-pixel head, two pointed ears, one bright eye and a light muzzle.
    poly(d, [(x, y), (x, y-3), (x+2, y-1), (x+4, y-1), (x+6, y-3),
             (x+6, y+2), (x+7, y+3), (x+6, y+4), (x+2, y+4), (x, y+2)], p['edge'])
    poly(d, [(x+1, y), (x+2, y-1), (x+4, y), (x+5, y-1),
             (x+6, y+2), (x+5, y+3), (x+2, y+3), (x+1, y+2)], p['fur'])
    points(d, [(x+1, y-1), (x+5, y-1)], p['nose'])
    points(d, [(x+2, y), (x+3, y)], p['furlight'])
    points(d, [(x+3, y+3), (x+4, y+3), (x+5, y+3)], p['muzzle'])
    points(d, [(x+6, y+2)], p['nose'])
    if closed:
        d.line([(x+3, y+1), (x+4, y+1)], fill=p['eye'])
    else:
        points(d, [(x+4, y+1)], p['iris'])
        points(d, [(x+5, y+1)], p['eye'])


def cat(pose, phase):
    im, d, p = canvas('cat')
    contacts = []
    if pose == 'sleep':
        top = 10 - (phase == 1)
        poly(d, [(6, 13), (7, top+1), (10, top), (14, top), (17, 11),
                 (18, 14), (16, 16), (9, 16), (6, 15)], p['edge'])
        poly(d, [(7, 13), (9, top+1), (13, top+1), (16, 12), (16, 14), (13, 15), (8, 15)], p['fur'])
        d.line([(9, top+1), (12, top+1), (14, top+2)], fill=p['furlight'])
        points(d, [(10, top+2), (12, top+3), (8, 14)], p['furshadow'])
        cat_head(d, p, 14, 11, closed=True)
        # Curled tail lies across the forepaws; it stays connected to the haunch.
        d.line([(7, 13), (6, 15), (9, 16), (14, 16), (17, 15)], fill=p['edge'], width=2)
        d.line([(7, 14), (8, 15), (13, 15), (15, 14)], fill=p['furlight'])
        points(d, [(10, 15), (13, 15)], p['furshadow'])
        contacts = [[10, 16], [14, 16]]
    elif pose == 'sit':
        # Tail curls around a tall seated haunch while two cream forepaws stay planted.
        d.line([(12, 13), (9, 16), (5, 16), (4, 14), (5, 13)], fill=p['edge'], width=2)
        d.line([(11, 14), (8, 15), (5, 15)], fill=p['furlight'])
        poly(d, [(11, 9), (14, 7), (17, 9), (18, 13), (18, 16), (11, 16), (9, 14)], p['edge'])
        poly(d, [(12, 9), (14, 8), (16, 9), (16, 14), (12, 15), (10, 14)], p['fur'])
        d.line([(14, 9), (15, 12), (15, 15)], fill=p['cream'], width=2)
        d.line([(17, 12), (17, 15)], fill=p['furlight'])
        points(d, [(14, 16), (15, 16), (17, 16), (18, 16)], p['muzzle'])
        d.line([(11, 11), (12, 12)], fill=p['furshadow'])
        d.line([(11, 13), (12, 14)], fill=p['furshadow'])
        cat_head(d, p, 12, 5, closed=phase == 1)
        if phase == 2:
            points(d, [(13, 3)], p['furlight'])
        contacts = [[14, 16], [17, 16]]
    elif pose == 'stretch':
        # Anticipation -> bow -> extended bow -> recovery. Paws remain at y16.
        bow = (0, 1, 2, 0)[phase]
        if bow == 0:
            return cat('walk', 1)
        d.line([(7, 9), (4, 6), (3, 3), (4, 2)], fill=p['edge'], width=2)
        d.line([(6, 8), (4, 5), (4, 3)], fill=p['fur'])
        poly(d, [(6, 7), (9, 6), (12, 8), (15, 10), (18, 11), (17, 14),
                 (13, 13), (10, 11), (8, 12), (6, 11)], p['edge'])
        poly(d, [(7, 8), (9, 7), (12, 9), (15, 11), (16, 12), (13, 12), (10, 10), (7, 10)], p['fur'])
        d.line([(8, 7), (10, 8), (12, 10), (15, 11)], fill=p['furlight'])
        points(d, [(9, 9), (11, 10), (13, 11)], p['furshadow'])
        d.line([(8, 11), (7, 14), (6, 16)], fill=p['edge'], width=2)
        d.line([(9, 11), (9, 14), (10, 16)], fill=p['furshadow'])
        d.line([(15, 13), (18, 15), (21, 16)], fill=p['edge'], width=2)
        d.line([(15, 13), (18, 15), (21, 15)], fill=p['furlight'])
        points(d, [(6, 16), (7, 16), (20, 16), (21, 16), (22, 16)], p['cream'])
        cat_head(d, p, 16, 10 + (bow == 2), closed=bow == 2)
        contacts = [[6, 16], [21, 16]]
    else:
        feet = ((6, 15, 10, 18), (8, 16, 8, 16), (10, 18, 6, 15), (8, 16, 8, 16))[phase]
        # Hooked tail sways by one pixel, with the tail base always joined.
        tip = 3 + (phase in (1, 2))
        d.line([(7, 10), (4, 8), (2, 6), (2, tip), (3, tip-1)], fill=p['edge'], width=2)
        d.line([(6, 9), (3, 7), (3, tip)], fill=p['fur'])
        points(d, [(3, 6)], p['furlight'])
        for x, toe in zip((8, 16), feet[:2]):
            d.line([(x, 11), (x, 13), (toe, 15)], fill=p['furshadow'], width=2)
            points(d, [(toe, 15)], p['edge'])
        poly(d, [(6, 9), (7, 7), (11, 7), (13, 8), (16, 7), (19, 9),
                 (19, 12), (16, 13), (9, 13), (6, 11)], p['edge'])
        poly(d, [(7, 9), (8, 8), (11, 8), (14, 9), (17, 8), (18, 10),
                 (16, 12), (10, 12), (7, 11)], p['fur'])
        d.line([(8, 8), (11, 8), (14, 9)], fill=p['furlight'])
        for x, y in ((9, 9), (12, 9), (15, 10)):
            d.line([(x, y), (x+1, y+1)], fill=p['furshadow'])
        for x, toe in zip((8, 16), feet[2:]):
            d.line([(x, 12), (x, 14), (toe, 16)], fill=p['edge'], width=2)
            d.line([(x, 12), (toe, 15)], fill=p['fur'])
            points(d, [(toe, 16), (toe+1, 16)], p['cream'])
        cat_head(d, p, 15, 7, closed=False)
        contacts = [[feet[2], 16], [feet[3], 16]]
    return im, {'ground_contacts': contacts}


BIRD_PATTERNS = {
    'stand': [
        '............', '............', '.......www..', '......wlccw.',
        '......wceeeb', '...wwwwclw..', '.wwbwwllw...', '..wwbblcw...',
        '....wccw....', '.....d.d....', '....dd.dd...', '............'],
    'blink': [
        '............', '............', '.......www..', '......wlccw.',
        '......wcddeb', '...wwwwclw..', '.wwbwwllw...', '..wwbblcw...',
        '....wccw....', '.....d.d....', '....dd.dd...', '............'],
    'dip': [
        '............', '............', '............', '............',
        '...www......', '.wwbwwww....', '..wwbblcww..', '....wccclcw.',
        '.....wwcwceb', '.....d.d..b.', '....dd.dd...', '............'],
    'peck': [
        '............', '............', '............', '............',
        '...www......', '.wwbwwww....', '..wwbbllw...', '....wccclww.',
        '.....wwwclw.', '.....d.dweb.', '....dd.dd.b.', '............'],
    'up': [
        '...d........', '..dwl.......', '..dwcl...ww.', '...dwcl.wccw',
        '....dwclwceb', '..wwwwclclw.', '.wwbbllccw..', '....wwwww...',
        '............', '............', '............', '............'],
    'wide': [
        '............', '............', '........ww..', '.......wccw.',
        '.ddww..wceeb', '..wwlwwlclw.', '...wwllccw..', '..wwwwwww...',
        '.ddwl.......', '..dd........', '............', '............'],
    'down': [
        '............', '............', '........ww..', '.......wccw.',
        '.......wceeb', '..wwwwwlclw.', '.wwbwlcccw..', '....wlwww...',
        '....wcld....', '.....wcld...', '......wdd...', '............'],
    'land': [
        '............', '............', '...d....ww..', '..dwl..wccw.',
        '..dwcl.wceeb', '...dwcllclw.', '.wwbwlcccw..', '..wwwclww...',
        '.....wcd....', '.....d.d....', '....dd.dd...', '............'],
}


def pixel_pattern(rows, palette, key):
    assert len(rows) == 12 and all(len(row) == 12 for row in rows)
    im = Image.new('RGBA', (12, 12))
    for y, row in enumerate(rows):
        for x, char in enumerate(row):
            if char != '.':
                im.putpixel((x, y), tuple(bytes.fromhex(palette[key[char]][1:])) + (255,))
    return im


def bird(pose, phase):
    kinds = {'peck': ['stand', 'dip', 'peck', 'stand'],
             'fly': ['up', 'wide', 'down', 'wide'],
             'land': ['up', 'land', 'stand']}[pose]
    kind = kinds[phase]
    key = {'w': 'edge', 'd': 'deep', 'b': 'brown', 'l': 'wing', 'c': 'cream', 'e': 'eye'}
    im = pixel_pattern(BIRD_PATTERNS[kind], PALETTES['bird'], key)
    # Separate warm face/beak pixels from the dark eye so the eye reads at 1x.
    if kind in ('stand', 'blink', 'up', 'wide', 'down', 'land'):
        x, y = (10, 4)
        im.putpixel((x, y), tuple(bytes.fromhex(PALETTES['bird']['light'][1:])) + (255,))
        im.putpixel((11, y), tuple(bytes.fromhex(PALETTES['bird']['beak'][1:])) + (255,))
    beak = [10, 10] if kind == 'peck' else [11, 8] if kind == 'dip' else [11, 4]
    return im, {'beak': beak, 'airborne': pose == 'fly' or (pose == 'land' and phase == 0),
                'ground_contacts': [] if pose == 'fly' or (pose == 'land' and phase == 0) else [[5, 10], [7, 10]]}


BUTTERFLY_PATTERNS = {
    'open': [
        '............', '...d...d....', '.dd.d.d.dd..', '.dLgdddLgLd.',
        '.dgggddgggd.', '..dggddggd..', '..dgsddsgd..', '..dggddggd..',
        '...dLddLd...', '....dddd....', '.....d......', '............'],
    'half': [
        '............', '....d.d.....', '..dd.d.dd...', '..dLdddLd...',
        '..dggdggd...', '...dgddgd...', '...dsddsd...', '...dgddgd...',
        '....LddL....', '.....dd.....', '.....d......', '............'],
    'closed': [
        '............', '....d.d.....', '.....ddd....', '.....dLgd...',
        '.....dggd...', '.....dgsd...', '.....dggd...', '.....dgd....',
        '.....dd.....', '.....dd.....', '.....d......', '............'],
    'rest': [
        '............', '............', '.....ddd....', '.....dLgd...',
        '....ddggd...', '.....dggd...', '.....dgsd...', '.....dggd...',
        '.....dgd....', '.....dd.....', '....ddd.....', '............'],
}


def butterfly(pose, phase):
    kind = ['open', 'half', 'closed', 'half'][phase] if pose == 'flutter' else ['rest', 'closed'][phase]
    im = pixel_pattern(BUTTERFLY_PATTERNS[kind], PALETTES['butterfly'],
                       {'d': 'edge', 'g': 'gold', 'L': 'light', 's': 'shadow'})
    return im, {'airborne': pose == 'flutter', 'ground_contacts': [] if pose == 'flutter' else [[5, 10]]}


# Purposeful pauses and contacts; finite entrance/action clips explicitly do not loop.
CLIPS = {
    'sheep': {'graze': ([.60, .22, .32, .44], True), 'walk': ([.19, .16, .19, .16], True),
              'look': ([1.30, .10, .65], True), 'nuzzle': ([.35, .28, .60, .40], False)},
    'cat': {'sleep': ([1.20, 1.20], True), 'stretch': ([.30, .44, .70, .32], False),
            'walk': ([.18, .14, .18, .14], True), 'sit': ([1.40, .12, .70], True)},
    'bird': {'land': ([.12, .16, .28], False), 'peck': ([.70, .16, .14, .35], True),
             'fly': ([.10, .08, .10, .08], True)},
    'butterfly': {'flutter': ([.10, .09, .10, .09], True), 'settle': ([1.00, .22], True)},
}


def png(im):
    buf = BytesIO()
    im.save(buf, format='PNG', optimize=True)
    return buf.getvalue()


def json_bytes(obj):
    return (json.dumps(obj, indent=2) + '\n').encode()


def mirrored_contacts(record, width):
    result = dict(record)
    for name in ('muzzle', 'beak'):
        if name in result:
            result[name] = [width - 1 - result[name][0], result[name][1]]
    result['ground_contacts'] = [[width - 1 - x, y] for x, y in record.get('ground_contacts', [])]
    return result


def animation_preview(manifest, frames):
    """Art-only board at recorded clip timing; finite clips hold then replay."""
    names = [name for name in manifest['clips'] if name.endswith('_right')]
    images = []
    for tick in range(200):
        scene = Image.new('RGB', (432, 5*88), '#687b50')
        d = ImageDraw.Draw(scene)
        for index, name in enumerate(names):
            x, y = (index % 3)*144, (index // 3)*88
            clip = manifest['clips'][name]
            durations = clip['durations']
            total = sum(durations)
            elapsed = (tick*.04) % (total + (0 if clip['loop'] else .80))
            frame = len(durations)-1
            for i, duration in enumerate(durations):
                if elapsed < duration:
                    frame = i
                    break
                elapsed -= duration
            im = frames[clip['frames'][frame]]
            size = tuple(n*3 for n in im.size)
            enlarged = im.resize(size, Image.Resampling.NEAREST)
            anchor = FAMILIES[clip['family']]['anchor']
            scene.paste(enlarged, (x+72-anchor[0]*3, y+68-anchor[1]*3), enlarged)
            d.text((x+8, y+5), name.removesuffix('_right').replace('_', ' '), fill='#fff1d4')
        d.text((8, 5*88-12), '3x native pixels / authored timing / art preview', fill='#fff1d4')
        images.append(scene)
    buf = BytesIO()
    images[0].save(buf, format='GIF', save_all=True, append_images=images[1:],
                   duration=40, loop=0, disposal=2, optimize=False)
    return buf.getvalue()


def products():
    files, frames = {}, {}
    manifest = {'version': 1, 'families': FAMILIES, 'clips': {},
                'props': {'seeds': {'file': 'seeds.png', 'size': [16, 8], 'anchor': [8, 6]}}}
    draw_family = {'sheep': sheep, 'cat': cat, 'bird': bird, 'butterfly': butterfly}
    for family, poses in CLIPS.items():
        for pose, (durations, loop) in poses.items():
            for direction in ('right', 'left'):
                name = f'{family}_{pose}_{direction}'
                clip = {'family': family, 'frames': [], 'durations': durations, 'loop': loop,
                        'landmarks': []}
                for index in range(len(durations)):
                    im, landmarks = draw_family[family](pose, index)
                    if direction == 'left':
                        im = im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                        landmarks = mirrored_contacts(landmarks, im.width)
                    filename = f'{name}_{index}.png'
                    clip['frames'].append(filename)
                    clip['landmarks'].append(landmarks)
                    files[OUT / filename] = png(im)
                    frames[filename] = im
                manifest['clips'][name] = clip
    # A restrained, sparse spill is one static ground prop, with no collected item.
    seed = Image.new('RGBA', (16, 8))
    d = ImageDraw.Draw(seed)
    for x, y in [(2, 4), (5, 2), (7, 5), (10, 3), (13, 5), (9, 1)]:
        d.point((x, y+1), fill='#8b6b4d')
        d.line([(x, y), (x+1, y)], fill='#d9b88e')
        d.point((x, y), fill='#f5d9b3')
    files[OUT / 'seeds.png'] = png(seed)
    files[OUT / 'animation.json'] = json_bytes(manifest)
    files[SOURCE / 'palette.json'] = json_bytes(PALETTES)
    # One row per action, at native size and integer enlargement, all source poses.
    cell_w, cell_h = 88, 38
    rows = sum(len(poses) for poses in CLIPS.values())
    sheet = Image.new('RGB', (6*cell_w, (rows+1)*cell_h), '#687b50')
    sd = ImageDraw.Draw(sheet)
    row = 0
    for family, poses in CLIPS.items():
        for pose in poses:
            y = row*cell_h
            sd.text((4, y+2), family + ' ' + pose, fill='#fff1d4')
            clip = manifest['clips'][f'{family}_{pose}_right']
            for i, filename in enumerate(clip['frames']):
                im = frames[filename]
                x = (i+2)*cell_w+30
                sheet.paste(im, (x, y+15), im)
                sd.text((x+27, y+19), f"{int(clip['durations'][i]*1000)}", fill='#d4d6ba')
            row += 1
    sd.text((4, row*cell_h+2), 'Original scale references / seed spill', fill='#fff1d4')
    for i, name in enumerate(('sheep_1', 'sheep_2', 'bird_1', 'bird_2', 'butterfly_1', 'butterfly_2')):
        im = Image.open(ORIGINAL / f'{name}.png').convert('RGBA')
        sheet.paste(im, (i*cell_w+22, row*cell_h+16), im)
    files[SOURCE / 'contacts_native.png'] = png(sheet)
    files[SOURCE / 'contacts_3x.png'] = png(sheet.resize((sheet.width*3, sheet.height*3), Image.Resampling.NEAREST))
    files[SOURCE / 'poses_preview.gif'] = animation_preview(manifest, frames)
    originals = [ORIGINAL / f'{animal}_{index}.png' for animal in ('sheep', 'bird', 'butterfly') for index in (1, 2)]
    provenance = {'version': 1, 'method': 'Hand-authored native pixel contours, articulated legs and purpose-specific heads/wings. No image generation, warping or interpolation.',
                  'builder': 'tools/build_regional_wildlife.py',
                  'builder_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  'original_references': [{'file': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()} for path in originals],
                  'palette': 'assets/source/characters/regional_wildlife/palette.json',
                  'review': ['assets/source/characters/regional_wildlife/contacts_native.png', 'assets/source/characters/regional_wildlife/contacts_3x.png'],
                  'registration': 'Ground anchor is the fixed near-foot pixel row. Flight elevation belongs to the controller. Left poses mirror native pixels around the canvas midline.',
                  'basket': 'Reuse assets/characters/garden_workers/basket.png as a separate controller-owned empty prop; none is baked into the sheep.',
                  'exports': [{'file': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(data).hexdigest()} for path, data in files.items() if path.parent == OUT]}
    files[OUT / 'provenance.json'] = json_bytes(provenance)
    return files


def build(check=False):
    mismatches = []
    for path, data in products().items():
        if check:
            if not path.exists() or path.read_bytes() != data:
                mismatches.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    if mismatches:
        raise SystemExit('Wildlife exports differ:\n' + '\n'.join(mismatches))
    print('Wildlife exports match native recipes.' if check else 'Built regional wildlife pixels, clips and contact sheets.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    build(parser.parse_args().check)
