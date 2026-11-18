"""Build the miller's costume and registered quest poses on shared silhouettes.

The approved male turnaround/walk template supplies scale; Caelan and Tomas's
approved walks supply stride and bob. No approved source sprite is overwritten.
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'assets/story/halden'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2)+'\n')


def save(name, image):
    path = OUT/name
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return path.relative_to(ROOT).as_posix()


def sack():
    im = Image.new('RGBA', (16, 18));d = ImageDraw.Draw(im)
    d.polygon([(6, 0), (11, 0), (10, 3), (14, 6), (15, 14), (12, 17), (3, 17), (0, 14), (1, 6), (6, 3)], fill='#30271e')
    d.polygon([(6, 4), (10, 4), (13, 7), (13, 14), (11, 15), (4, 15), (2, 13), (3, 7)], fill='#b99a6d')
    d.line((5, 5, 4, 13), fill='#d1b486');d.line((11, 6, 12, 13), fill='#8c704f')
    d.line((6, 2, 10, 2), fill='#6c5438');d.line((4, 16, 11, 16), fill='#8c704f')
    for point in ((7, 8), (9, 10), (6, 12)):d.point(point, fill='#9b7b52')
    return im


def miller(base, direction):
    im = base.copy()
    colors = {'#3d2118': '#626763', '#71452c': '#92968a', '#9d6238': '#c6c4ad',
              '#455531': '#435c68', '#6e7d43': '#657e89', '#919b61': '#92a4a3'}
    mapping = {tuple(bytes.fromhex(a[1:])): tuple(bytes.fromhex(b[1:])) for a, b in colors.items()}
    for y in range(36):
        for x in range(24):
            p = im.getpixel((x, y))
            if p[3] and p[:3] in mapping:im.putpixel((x, y), (*mapping[p[:3]], 255))
    d = ImageDraw.Draw(im)
    # Short gray beard, receding temples, and an oatmeal miller's apron.
    if direction == 'front':
        d.polygon([(9, 10), (10, 12), (13, 12), (15, 10), (14, 13), (10, 13)], fill='#92968a')
        d.line((10, 10, 13, 10), fill='#c6c4ad')
        d.rectangle((10, 16, 13, 22), fill='#d1b486')
        d.rectangle((9, 22, 14, 28), fill='#b99a6d');d.line((10, 24, 10, 27), fill='#e1cfab')
        d.line((11, 2, 13, 2), fill='#e8c49d')
    elif direction in ('left', 'right'):
        x = 8 if direction == 'left' else 14
        d.rectangle((x, 11, x+1, 13), fill='#92968a')
        d.line((x, 11, x+1, 11), fill='#c6c4ad')
        x = 8 if direction == 'left' else 13
        d.rectangle((x, 18, x+2, 27), fill='#b99a6d')
        d.line((x, 19, x, 25), fill='#d1b486')
    else:
        d.line((9, 16, 14, 23), fill='#b99a6d');d.line((14, 16, 9, 23), fill='#b99a6d')
    return im


def carry(body, direction, bag, bob=0, lowered=0):
    im = Image.new('RGBA', (32, 40));im.alpha_composite(body, (4, 4))
    point = {'front': (8, 17), 'left': (2, 16), 'right': (14, 16), 'back': (8, 17)}[direction]
    pos = (point[0], point[1]+bob+lowered)
    if direction == 'back':
        behind = Image.new('RGBA', im.size);behind.alpha_composite(bag, pos);behind.alpha_composite(im);im = behind
    else:
        im.alpha_composite(bag, pos)
        d = ImageDraw.Draw(im)
        # Bent close-contact hands. Forearms project only two native pixels.
        for x in ([8, 23] if direction == 'front' else [pos[0]+3, pos[0]+12]):
            d.rectangle((x, pos[1]+9, x+1, pos[1]+11), fill='#e8c49d')
    return im


def build():
    bag = sack();save(Path('sack.png'), bag)
    pallet = Image.new('RGBA', (76, 26));d = ImageDraw.Draw(pallet)
    d.rectangle((1, 5, 74, 24), fill='#573422')
    for y in (6, 12, 18):
        d.rectangle((2, y, 73, y+4), fill='#84512e');d.line((3, y, 72, y), fill='#b77740')
    for x in (7, 67):d.line((x, 5, x, 23), fill='#573422')
    save(Path('pallet.png'), pallet)
    bottle = Image.new('RGBA', (5, 9));d = ImageDraw.Draw(bottle)
    d.rectangle((1, 0, 3, 2), fill='#84512e');d.rectangle((0, 3, 4, 8), fill='#30271e')
    d.rectangle((1, 3, 3, 7), fill='#667e69');d.rectangle((1, 4, 3, 5), fill='#e1cfab')
    save(Path('medicine.png'), bottle)
    for direction in ('front', 'left', 'right', 'back'):
        base = Image.open(ROOT/f'assets/characters/npcs/male_01/idle_{direction}.png').convert('RGBA')
        save(Path(f'idle_{direction}.png'), miller(base, direction))
        for character in ('caelan', 'tomas'):
            idle = Image.open(ROOT/f'assets/characters/{character}/idle_{direction}.png').convert('RGBA')
            save(Path(f'{character}/hold_{direction}.png'), carry(idle, direction, bag))
            folder = ROOT/f'assets/characters/{character}/walk_{direction}'
            metadata = json.loads((folder/'animation.json').read_text())
            for i, frame in enumerate(metadata['frames']):
                body = Image.open(folder/frame['file']).convert('RGBA')
                bob = frame.get('upper_body_offset', [0, 0])[1]
                save(Path(f'{character}/carry_{direction}_{i}.png'), carry(body, direction, bag, bob))
            # Four lift/set-down poses. Contact starts at frame 2 (zero-based).
            for i, drop in enumerate((5, 3, 1, 0)):
                save(Path(f'{character}/lift_{direction}_{i}.png'), carry(idle, direction, bag, lowered=drop))
    write(OUT/'art.json', {
        'frame_size': [24, 36], 'actor_anchor': [12, 30],
        'carry_canvas': [32, 40], 'carry_anchor': [16, 34],
        'source': 'Approved male NPC silhouette and Caelan/Tomas four-frame stride templates',
        'design': 'Gray beard and hair, slate-blue shirt, flour-colored apron; restrained close-contact sack poses',
        'lift_duration_ms': 720, 'contact_frame': 2,
        'directions': ['front', 'left', 'right', 'back']})


if __name__ == '__main__':build()
