"""Elira's costume and registered lantern poses on approved shared silhouettes."""
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'assets/story/elira'
SIZE = (40, 64)
OFFSET = (8, 24)
ANCHOR = (20, 54)


def load(path):return Image.open(ROOT/path).convert('RGBA')


def save(name, image):
    path = OUT/name;path.parent.mkdir(parents=True, exist_ok=True);image.save(path)


def color(value):return (*bytes.fromhex(value[1:]), 255)


def costume(image, direction):
    image = image.copy()
    materials = {
        'hair': (['#302329', '#4b373c', '#70535a'], ['#514a4a', '#817a75', '#beb6a3']),
        'dress': (['#304f70', '#4d77a0', '#7da5c7'], ['#664856', '#946774', '#bd8c90']),
        'eyes': (['#356c9b'], ['#80623e'])}
    for material, (source, target) in materials.items():
        mapping = {color(a): color(b) for a, b in zip(source, target)}
        for y in range(36):
            if material == 'hair' and y>14:continue
            for x in range(24):
                p = image.getpixel((x, y))
                if p in mapping:image.putpixel((x, y), mapping[p])
    d = ImageDraw.Draw(image)
    if direction == 'front':
        d.polygon([(9, 19), (14, 19), (15, 28), (8, 28)], fill='#d1bfa0')
        d.line((10, 21, 10, 27), fill='#e5d8b9');d.line((13, 22, 14, 28), fill='#b19c7f')
        d.line((9, 16, 9, 20), fill='#d1bfa0');d.line((14, 16, 14, 20), fill='#d1bfa0')
    elif direction in ('left', 'right'):
        x = 8 if direction == 'left' else 14
        d.rectangle((x, 20, x+1, 28), fill='#d1bfa0')
        d.point((x, 23), fill='#e5d8b9')
    else:d.line((9, 20, 14, 20), fill='#b19c7f')
    # A modest shawl follows the shoulders, leaving the face and neckline clear.
    for x in range(7, 17):
        if image.getpixel((x, 15))[3]:
            d.point((x, 15), fill='#6e785b')
            if x in (7, 8, 15, 16):d.point((x, 16), fill='#9ca080')
    return image


def elbow(shoulder, wrist, bend):
    """Two six-pixel arm segments; wrist paths never lengthen an arm."""
    dx, dy = wrist[0]-shoulder[0], wrist[1]-shoulder[1]
    distance = math.hypot(dx, dy)
    assert distance <= 12.01
    if distance<.001:return (shoulder[0]+6*bend, shoulder[1])
    height = math.sqrt(max(0, 36-distance*distance/4))
    return (round((shoulder[0]+wrist[0])/2-dy/distance*height*bend),
            round((shoulder[1]+wrist[1])/2+dx/distance*height*bend))


def arms(body, right=(20, 24), left=None, bob=0):
    body = body.copy();d = ImageDraw.Draw(body)
    # Erase just the hanging near arm, preserving the torso and approved head.
    for side, wrist, shoulder in [('right', right, (16, 15)), ('left', left, (7, 15))]:
        if wrist is None:continue
        x0, x1 = (16, 23) if side == 'right' else (0, 7)
        d.rectangle((x0, 14+bob, x1, 25+bob), fill=(0, 0, 0, 0))
        shoulder = (shoulder[0], shoulder[1]+bob);wrist = (wrist[0], wrist[1]+bob)
        mid = elbow(shoulder, wrist, -1 if side == 'right' else 1)
        d.line([shoulder, mid, wrist], fill='#1a0e16', width=3)
        d.line([shoulder, mid, wrist], fill='#fbeed0', width=2)
        d.rectangle((wrist[0], wrist[1], wrist[0]+1, wrist[1]+1), fill='#e8c49d')
    return body


def canvas(body, lantern=None, origin=(18, 2), behind=False):
    image = Image.new('RGBA', SIZE)
    pos = (OFFSET[0]+origin[0], OFFSET[1]+origin[1])
    if lantern is not None and behind:image.alpha_composite(lantern, pos)
    image.alpha_composite(body, OFFSET)
    if lantern is not None and not behind:image.alpha_composite(lantern, pos)
    return image


def build():
    lantern = load('assets/terrain/eldenmere/elira_interior/sprites/lantern_unlit.png')
    sources = {}
    for direction in ('front', 'left', 'right', 'back'):
        path = f'assets/characters/npcs/female_01/idle_{direction}.png'
        body = load(path);save(Path(f'idle_{direction}.png'), costume(body, direction))
        sources[path] = hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
        idle = load(f'assets/characters/caelan/idle_{direction}.png')
        folder = ROOT/f'assets/characters/caelan/walk_{direction}'
        frames = json.loads((folder/'animation.json').read_text())['frames']
        for index in range(5):
            frame = frames[(index-1)%4] if index else None
            source = load((folder/frame['file']).relative_to(ROOT)) if frame else idle
            bob = frame.get('upper_body_offset', [0, 0])[1] if frame else 0
            left = direction == 'left'
            body = arms(source, right=None if left else (20, 24), left=(3, 24) if left else None, bob=bob)
            name = f'carry_{direction}_{index-1}.png' if frame else f'hold_{direction}.png'
            save(Path(name), canvas(body, lantern, (-6, 2+bob) if left else (18, 2+bob), direction=='back'))
        # A small provision bundle is held close rather than stretching toward her.
        give = arms(idle, right=(20, 24))
        save(Path(f'give_{direction}.png'), canvas(give))

    back = load('assets/characters/caelan/idle_back.png')
    for index in range(4):
        f = index/3
        wrist = (round(20-4*f), round(24-21*f))
        left = (round(3+4*f), round(24-21*f))
        save(Path(f'reach_{index}.png'), canvas(arms(back, wrist, left)))
        origin = (round(6+12*f), round(-19+21*f))
        wrist = (round(16+4*f), round(3+21*f))
        left = (round(7-4*f), round(3+21*f))
        save(Path(f'take_{index}.png'), canvas(arms(back, wrist, left), lantern, origin, behind=True))
        # Bent knee steps use the approved walk; logical feet stay on valid floor.
        step = load(f'assets/characters/caelan/walk_back/frame_{index+1:02}.png')
        save(Path(f'step_{index}.png'), canvas(step))
        save(Path(f'down_{index}.png'), canvas(arms(step), lantern, behind=True))

    front = load('assets/characters/caelan/idle_front.png')
    for index in range(4):
        f = index/3;wrist = (round(20-6*f), round(24+2*f))
        origin = (round(18-8*f), round(2+6*f))
        body = arms(front, wrist)
        save(Path(f'place_{index}.png'), canvas(body, lantern, origin))
        save(Path(f'place_empty_{index}.png'), canvas(body))

    provisions = Image.new('RGBA', (16, 14));d = ImageDraw.Draw(provisions)
    d.rectangle((1, 6, 14, 13), fill='#654e3c');d.rectangle((2, 7, 13, 11), fill='#b79a6c')
    d.rounded_rectangle((2, 3, 9, 8), radius=2, fill='#c6965e');d.line((4, 3, 7, 3), fill='#e0bf8c')
    d.rectangle((10, 2, 14, 8), fill='#737e7a');d.rectangle((11, 0, 13, 2), fill='#836347')
    d.line((11, 4, 11, 6), fill='#d3b56a');save(Path('provisions.png'), provisions)
    (OUT/'art.json').write_text(json.dumps({
        'character': 'elira', 'frame_size': [24, 36], 'draw_anchor': [12, 30],
        'pose_canvas': list(SIZE), 'pose_anchor': list(ANCHOR),
        'source_hashes': sources, 'arm_segment_length': 6,
        'lantern': 'assets/terrain/eldenmere/elira_interior/sprites/lantern_unlit.png',
        'contact': {'player_visual_feet': [154, 76], 'lantern_world_origin': [148, 27],
                    'take_frame': 0, 'shelf_frame': 'shelf_with_lantern.png'},
        'design': 'Silver-streaked low bun, hazel eyes, mulberry dress, oatmeal apron, sage shawl',
        'stride_source': 'Approved Caelan four-frame walking animations, with coordinated bob'
    }, indent=2)+'\n')


if __name__ == '__main__':build()
