try:
    from tools.caelan_reference import open_image
except ModuleNotFoundError:
    from caelan_reference import open_image
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


def load(path):return open_image(ROOT/path).convert('RGBA')


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


def build():
    lantern = load('assets/terrain/eldenmere/elira_interior/sprites/lantern_unlit.png')
    sources = {}
    for direction in ('front', 'left', 'right', 'back'):
        path = f'assets/characters/npcs/female_01/idle_{direction}.png'
        body = load(path);save(Path(f'idle_{direction}.png'), costume(body, direction))
        sources[path] = hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
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
        'player_art': 'assets/characters/caelan/scene_actions.json'
    }, indent=2)+'\n')


if __name__ == '__main__':
    build()
    from export_caelan_scene_actions_hd import build as build_caelan
    build_caelan()
