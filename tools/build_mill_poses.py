"""Build the mill's modest successful spell and grounded cooperative poses.

Approved source bodies keep their ordinary registration. Caelan's forearm uses
his reviewed casting study. Mira's far arm rotates about a stationary shoulder;
her head, hips, legs and boots are never shifted or redrawn.
"""
from pathlib import Path
import hashlib
import json
import math
from PIL import Image, ImageDraw
from build_venn_magicks import native_layers

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'assets/story/mill/poses'
SIZE = (40, 48)
OFFSET = (8, 8)
ANCHOR = (20, 38)
LAYERS = ['body', 'casting_arm', 'energy']
TIMELINE = [
    ('raise_hand', 650, [(90, 0), (65, 0), (40, 0), (15, 0), (-14, 0)]),
    ('move_water', 1200, [(-14, 1), (-14, 2), (-14, 1), (-14, 1), (-14, 1), (-14, 0)]),
    ('recover', 650, [(-14, 0), (15, 0), (40, 0), (65, 0), (90, 0)]),
]


def padded(image):
    canvas = Image.new('RGBA', SIZE)
    canvas.alpha_composite(image, OFFSET)
    return canvas


def build_caelan():
    source = ROOT/'assets/characters/caelan/idle_right.png'
    idle = Image.open(source).convert('RGBA')
    idle.save(OUT/'source_body.png')
    atlas_size = (max(len(frames) for _, _, frames in TIMELINE)*40, len(TIMELINE)*48)
    atlas = Image.new('RGBA', atlas_size)
    layers = {name: Image.new('RGBA', atlas_size) for name in LAYERS}
    animations = {}
    for row, (name, duration, specs) in enumerate(TIMELINE):
        records = []
        for column, (angle, energy) in enumerate(specs):
            parts, joints = native_layers(idle, angle, energy)
            native = Image.new('RGBA', (24, 36))
            for layer in LAYERS:native.alpha_composite(parts[layer])
            assert native.crop((0, 0, 24, 14)).tobytes() == idle.crop((0, 0, 24, 14)).tobytes()
            assert native.crop((0, 25, 24, 36)).tobytes() == idle.crop((0, 25, 24, 36)).tobytes()
            if angle == 90:assert native.tobytes() == idle.tobytes()
            rect = [column*40, row*48, 40, 48]
            atlas.alpha_composite(padded(native), rect[:2])
            for layer in LAYERS:layers[layer].alpha_composite(padded(parts[layer]), rect[:2])
            records.append({'rect': rect, 'angle_degrees': angle, 'energy_level': energy,
                            'casting_hand': [round(joints['wrist'][0])+8, round(joints['wrist'][1])+8],
                            'joints': {'casting': [[x+8, y+8] for x, y in joints.values()]}})
        animations[name] = {'duration_ms': duration, 'frames': records}
    atlas.save(OUT/'poses.png')
    for name, layer in layers.items():layer.save(OUT/(name+'.png'))
    (OUT/'animation.json').write_text(json.dumps({
        'canvas': list(SIZE), 'anchor': list(ANCHOR), 'source_canvas': [24, 36],
        'source_offset': list(OFFSET), 'source_body': 'source_body.png',
        'source_idle_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'layer_order': LAYERS, 'arm_lengths': [4, 4],
        'preserved_source_regions': {'head': [0, 0, 24, 14], 'lower_body': [0, 25, 24, 36]},
        'outcome': 'success', 'sequence': [name for name, _, _ in TIMELINE],
        'animations': animations,
        'effect': 'A small controlled movement of still water; no sustained force against a current.',
    }, indent=2)+'\n')


def arm_joints(wrist):
    shoulder = (13., 17.)
    dx, dy = wrist[0]-shoulder[0], wrist[1]-shoulder[1]
    distance = math.hypot(dx, dy)
    upper = forearm = 4.5
    assert 0 < distance <= upper+forearm
    along = distance/2
    height = math.sqrt(upper*upper-along*along)
    elbow = (shoulder[0]+dx*along/distance-dy*height/distance,
             shoulder[1]+dy*along/distance+dx*height/distance)
    return [shoulder, elbow, wrist]


def build_mira():
    directions = ROOT/'assets/source/characters/mira/directions'
    for direction in ('left', 'right', 'back'):
        source = Image.open(directions/f'appearance_{direction}.png').convert('RGBA')
        source.save(ROOT/f'assets/characters/mira/idle_{direction}.png')
    source_path = directions/'appearance_right.png'
    idle = Image.open(source_path).convert('RGBA')
    idle.save(OUT/'mira_source_body.png')
    # These body-registered stations put the last grip at actor+[6,-10].
    # The catch uses a small angled pick, whose end is actor+[10,-12].
    specs = {'bypass': [(16, 22), (17, 21), (18, 20), (18, 20)],
             'catch': [(16, 22), (17, 21), (18, 20), (18, 20)],
             'lever': [(16, 22), (17, 21), (18, 20), (18, 20)]}
    layer_order = ['body', 'tool', 'working_arm']
    metadata = {}
    sheets = {name: Image.new('RGBA', (160, 144)) for name in layer_order}
    atlas = Image.new('RGBA', (160, 144))
    for row, (action, wrists) in enumerate(specs.items()):
        frames = []
        for index, wrist in enumerate(wrists):
            body = idle.copy();tool = Image.new('RGBA', idle.size)
            arm = Image.new('RGBA', idle.size)
            # Remove only the old far-arm outline at the shirt's forward edge.
            for y in range(17, 21):
                for x in range(15, 17):body.putpixel((x, y), (0, 0, 0, 0))
            joints = arm_joints(wrist)
            rounded = [(round(x), round(y)) for x, y in joints]
            if action == 'catch':
                draw = ImageDraw.Draw(tool)
                tip = (22, 18)
                draw.line([rounded[-1], tip], fill='#485354', width=1)
                draw.line((21, 18, 22, 18, 22, 19), fill='#b8c9c6')
            else:tip = wrist
            draw = ImageDraw.Draw(arm)
            draw.line(rounded, fill='#1a0e16', width=3)
            draw.line(rounded[:2], fill='#cc7894', width=2)
            draw.line(rounded[1:], fill='#e8c49d', width=2)
            x, y = rounded[-1]
            draw.line((x, y, x+1, y), fill='#e8c49d')
            parts = {'body': body, 'tool': tool, 'working_arm': arm}
            native = Image.new('RGBA', (24, 36))
            for layer in layer_order:native.alpha_composite(parts[layer])
            assert native.crop((0, 0, 24, 17)).tobytes() == idle.crop((0, 0, 24, 17)).tobytes()
            assert native.crop((0, 26, 24, 36)).tobytes() == idle.crop((0, 26, 24, 36)).tobytes()
            assert set(native.getchannel('A').tobytes()) <= {0, 255}
            canvas = padded(native)
            filename = f'mira_{action}_{index}.png'
            canvas.save(OUT/filename)
            rect = [index*40, row*48, 40, 48]
            atlas.alpha_composite(canvas, rect[:2])
            for layer in layer_order:sheets[layer].alpha_composite(padded(parts[layer]), rect[:2])
            frames.append({'file': filename, 'duration_ms': 180, 'rect': rect,
                           'hand': [wrist[0]+8, wrist[1]+8],
                           'tool_tip': [tip[0]+8, tip[1]+8],
                           'joints': [[x+8, y+8] for x, y in joints]})
        metadata[action] = {'frames': frames, 'loop': False}
    atlas.save(OUT/'mira_poses.png')
    for name, sheet in sheets.items():sheet.save(OUT/f'mira_{name}.png')
    (OUT/'mira_animation.json').write_text(json.dumps({
        'canvas': list(SIZE), 'anchor': list(ANCHOR), 'source_canvas': [24, 36],
        'source_offset': list(OFFSET), 'source_body': 'mira_source_body.png',
        'source_idle_sha256': hashlib.sha256(source_path.read_bytes()).hexdigest(),
        'layer_order': layer_order, 'arm_lengths': [4.5, 4.5],
        'preserved_source_regions': {'head': [0, 0, 24, 17], 'lower_body': [0, 26, 24, 36]},
        'animations': metadata,
    }, indent=2)+'\n')


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    build_caelan();build_mira()


if __name__ == '__main__':build()
