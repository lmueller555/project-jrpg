"""Build Venn family appearances and the gate's accessible-bank repair poses."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw
from build_elira_visit import elbow
from build_eldenmere_gate import channel_assets, gate_frame, poses

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'assets/story/venn'
SIZE = (40, 48)
OFFSET = (8, 8)
ANCHOR = (20, 38)


def load(path):return Image.open(ROOT/path).convert('RGBA')


def read(path):return json.loads((ROOT/path).read_text())


def save(path, image):
    target = OUT/path;target.parent.mkdir(parents=True, exist_ok=True);image.save(target)


def rgba(c):return (*bytes.fromhex(c[1:]), 255)


def recolor(body, mapping, region=None):
    result = body.copy();mapping = {rgba(a): rgba(b) for a, b in mapping.items()}
    for y in range(body.height):
        for x in range(body.width):
            if region and not region(x, y):continue
            p = body.getpixel((x, y))
            if p in mapping:result.putpixel((x, y), mapping[p])
    return result


def family():
    hashes = {}
    for direction in ('front', 'left', 'right', 'back'):
        for member, source in [('mother', 'npcs/female_01'), ('father', 'npcs/male_01'), ('child', 'liam')]:
            path = f'assets/characters/{source}/idle_{direction}.png';body = load(path)
            hashes[path] = hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
            if member == 'mother':
                body = recolor(body, {'#304f70': '#305c59', '#4d77a0': '#4c8278', '#7da5c7': '#83aaa0',
                                      '#356c9b': '#805736'})
                d = ImageDraw.Draw(body)
                if direction == 'front':
                    d.polygon([(9, 19), (14, 19), (15, 29), (8, 29)], fill='#d8c39c')
                    d.line((10, 21, 10, 28), fill='#eee0bd');d.line((14, 22, 14, 28), fill='#ac9576')
                elif direction in ('left', 'right'):
                    x = 8 if direction == 'left' else 14
                    d.rectangle((x, 20, x+1, 28), fill='#d8c39c')
                else:d.line((9, 20, 14, 20), fill='#ac9576')
            elif member == 'father':
                body = recolor(body, {'#455531': '#694439', '#6e7d43': '#97614b', '#919b61': '#bc8563'})
                d = ImageDraw.Draw(body)
                if direction == 'front':d.rectangle((11, 16, 12, 22), fill='#e6d9ba')
                for x in (6, 7, 16, 17):
                    for y in range(17, 22):
                        if body.getpixel((x, y))[:3] in ((105, 68, 57), (151, 97, 75), (188, 133, 99)):
                            d.point((x, y), fill='#ded1ae')
            else:
                body = recolor(body, {'#8a601d': '#536f86', '#b88a2c': '#839eaf', '#d6ae50': '#b2c7ca',
                                      '#294f3c': '#536f86', '#476a46': '#839eaf', '#7b925b': '#b2c7ca'})
            save(Path(f'{member}/idle_{direction}.png'), body)
    front = load((OUT/'child/idle_front.png').relative_to(ROOT))
    head = Image.new('RGBA', (24, 36));head.alpha_composite(front.crop((0, 9, 24, 21)), (0, 4))
    d = ImageDraw.Draw(head);d.rectangle((11, 16, 13, 18), fill='#e8c49d')
    save(Path('child/rest_head.png'), head)
    asleep = head.copy();d = ImageDraw.Draw(asleep)
    for x in (10, 13):
        d.line((x, 12, x, 13), fill='#e8c49d');d.line((x-1, 13, x, 13), fill='#71452c')
    save(Path('child/rest_blink.png'), asleep)
    return hashes


def body_pose(index, mode):
    """Standing repair: fixed body, short bent arm and a tool for reach."""
    import math
    body = load('assets/characters/caelan/idle_right.png')
    image = Image.new('RGBA', SIZE)
    image.alpha_composite(body, OFFSET)
    d = ImageDraw.Draw(image)
    # The front/far shoulder is already on the mechanism side of the chest.
    # Rotate an anatomically short arm; the shaft, never the limb, spans the gap.
    shoulder = (22., 25.)
    wrists = [(27., 27.), (27., 25.), (28., 26.), (28., 27.)] if mode == 'tools' else [(28., 28.), (28., 27.), (28., 26.), (28., 25.)]
    wrist = wrists[index]
    dx, dy = wrist[0]-shoulder[0], wrist[1]-shoulder[1]
    distance = math.hypot(dx, dy);upper = 4.;forearm = 4.5
    along = (upper**2-forearm**2+distance**2)/(2*distance)
    height = math.sqrt(max(0., upper**2-along**2))
    joint = (shoulder[0]+dx*along/distance-dy*height/distance,
             shoulder[1]+dy*along/distance+dx*height/distance)
    points = [tuple(round(v) for v in p) for p in (shoulder, joint, wrist)]
    # Tools are behind the grip, but in front of the gate when the actor draws.
    if mode == 'tools':
        head = [(34, 26), (33, 23), (34, 26), (34, 27)][index]
        d.line((round(wrist[0])-2, round(wrist[1])+1, *head), fill='#836347', width=2)
        d.rectangle((head[0]-1, head[1]-1, head[0]+1, head[1]+1), fill='#737e7a')
        d.line((head[0]-1, head[1]-1, head[0]+1, head[1]-1), fill='#a4aaa0')
    else:
        # A modest borrowed hook clears debris and lifts the board. Its long
        # handle makes contact possible while both feet remain on the dry bank.
        tip = [(37, 26), (37, 25), (37, 24), (37, 23)][index]
        d.line((round(wrist[0])-2, round(wrist[1])+1, *tip), fill='#836347', width=1)
        d.line((tip[0]-2, tip[1], tip[0], tip[1], tip[0], tip[1]+2), fill='#737e7a', width=1)
        d.point((tip[0]-1, tip[1]), fill='#a4aaa0')
    d.line(points, fill='#1a0e16', width=3)
    d.line(points, fill='#fbeed0', width=1)
    x, y = points[-1]
    d.line((x, y, x+1, y), fill='#e8c49d')
    return image


def gate_assets():
    recipe = read('assets/source/terrain/eldenmere/gate/recipe.json')
    palette = read('assets/terrain/eldenmere/gate/palette.json')['materials']
    parts = {n: load(f'assets/source/terrain/eldenmere/gate/parts/{n}.png') for n in ('panel', 'post', 'stone', 'beam')}
    structure = load('assets/source/terrain/eldenmere/gate/parts/fixed_structure.png')
    _, tiles, _ = channel_assets();gate_tiles = tiles['channel_05_from_n']
    animations = {}
    for name, records in poses(recipe).items():
        animations[name] = []
        for i, pose in enumerate(records):
            path = Path(f'gate/{name}_{i}.png')
            save(path, gate_frame(pose, parts, structure, gate_tiles, palette, recipe, pin_side='left'))
            animations[name].append((OUT/path).relative_to(ROOT).as_posix())
    # Reconstruct only the small patch beneath the old baked gate. Source town
    # ground stays unchanged; the opaque patch prevents old pin/board ghosts.
    town = read('assets/maps/eldenmere/playable/map.json');backgrounds = []
    for i in range(6):
        phase_ground = load(town['ground_frames'][i])
        patch = phase_ground.crop((1440, 636, 1464, 672))
        # Strip the old gate with its underlying channel, retaining nearby grass.
        clean = Image.new('RGBA', patch.size)
        for y in range(36):
            for x in range(24):clean.putpixel((x, y), patch.getpixel((0 if x<12 else 23, y)))
        clean.alpha_composite(gate_tiles[i].crop((0, 12, 24, 24)), (0, 0))
        clean.alpha_composite(gate_tiles[i], (0, 12))
        path = Path(f'gate/background_{i}.png');save(path, clean.convert('RGB'))
        backgrounds.append((OUT/path).relative_to(ROOT).as_posix())
    return {'animations': animations, 'backgrounds': backgrounds}


def build():
    hashes = family()
    # Superseded generic casting frames are replaced by the held-water atlas.
    for i in range(4):(OUT/f'caelan/magicks_{i}.png').unlink(missing_ok=True)
    for mode in ('tools', 'hands'):
        for i in range(4):save(Path(f'caelan/{mode}_{i}.png'), body_pose(i, mode))
    for direction in ('front', 'back', 'left', 'right'):
        im = Image.new('RGBA', SIZE);im.alpha_composite(load(f'assets/characters/caelan/idle_{direction}.png'), OFFSET)
        save(Path(f'caelan/give_{direction}.png'), im)
    head = load((OUT/'child/rest_head.png').relative_to(ROOT))
    provisions = Image.new('RGBA', (18, 14));d = ImageDraw.Draw(provisions)
    d.rectangle((1, 6, 16, 13), fill='#836347');d.line((2, 6, 15, 6), fill='#b79a6c')
    d.rounded_rectangle((2, 3, 10, 8), radius=2, fill='#d3b486')
    d.rectangle((11, 2, 15, 8), fill='#667e69');d.rectangle((12, 0, 14, 2), fill='#84512e')
    save(Path('provisions.png'), provisions)
    tools = Image.new('RGBA', (20, 12));d = ImageDraw.Draw(tools)
    d.rectangle((0, 5, 19, 11), fill='#654e3c');d.rectangle((1, 6, 18, 9), fill='#a08158')
    d.line((4, 4, 13, 7), fill='#836347', width=2);d.rectangle((12, 2, 16, 5), fill='#737e7a')
    save(Path('toolbox.png'), tools)
    debris = Image.new('RGBA', (8, 13));d = ImageDraw.Draw(debris)
    d.line((3, 0, 5, 12), fill='#654e3c', width=2);d.line((0, 3, 7, 9), fill='#836347', width=2)
    d.line((2, 10, 6, 2), fill='#919b61');save(Path('debris.png'), debris)
    meta = {'source_hashes': hashes, 'frame_size': [24, 36], 'draw_anchor': [12, 30],
            'repair_canvas': list(SIZE), 'repair_anchor': list(ANCHOR),
            'gate_position': [1440, 636], 'pin_contact': [1442, 659], 'repair_approach': [1428, 670],
            'child': '26 visible pixels, resting on the existing pillow; full directional idles retained',
            'names': 'Parents and child are identified by family role; given names remain open', **gate_assets()}
    (OUT/'art.json').write_text(json.dumps(meta, indent=2)+'\n')


if __name__ == '__main__':
    build()
    from build_venn_magicks import build as build_magicks
    build_magicks()
