"""Build Caelan's unsuccessful water spell from the approved native-pixel study.

The head, upper body and lower body remain on the ordinary idle registration.
Only the near forearm rotates; a tiny palm spark gathers and fails. These frames
never contain a gate, held water, a kneel, or a displaced pelvis.
"""
from pathlib import Path
import hashlib
import json
import math

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'assets/story/venn/magicks'
SOURCE = ROOT/'assets/characters/caelan/idle_right.png'
SOURCE_SIZE = (24, 36)
SIZE = (40, 48)
OFFSET = (8, 8)
# This is the town's ordinary [12,30] draw anchor plus OFFSET. Caelan's visible
# feet remain four pixels below that collision reference, exactly as in idle.
ANCHOR = (20, 38)
OUTLINE = '#1a0e16'
CREAM = '#fbeed0'
SKIN = '#e8c49d'
TEAL = '#1f5d72'

# angle is the near forearm's angle about the unchanged elbow. Energy levels
# are small authored spark shapes, not an indication of water displacement.
TIMELINE = [
    ('raise_hand', 650, [(90, 0), (65, 0), (40, 0), (15, 0), (-14, 0)]),
    ('attempt', 1100, [(-14, 1), (-14, 2), (-14, 1), (-14, 3), (-14, 1), (-14, 3)]),
    ('fizzle', 600, [(-14, 3), (-14, 1), (-14, 4), (-14, 4), (-14, 0)]),
    ('recover', 650, [(-14, 0), (15, 0), (40, 0), (65, 0), (90, 0)]),
]
LAYER_ORDER = ['body', 'casting_arm', 'energy']


def native_layers(idle, angle, energy_level):
    """Return the approved study's three reconstructable, hard-alpha layers."""
    body = idle.copy()
    arm = Image.new('RGBA', SOURCE_SIZE)
    energy = Image.new('RGBA', SOURCE_SIZE)
    shoulder, elbow = (10, 16), (10, 20)
    rad = math.radians(angle)
    wrist = (10+4*math.cos(rad), 20+4*math.sin(rad))
    px, py = map(round, wrist)
    if angle != 90:
        # Reveal the tunic behind the original hanging forearm. The original
        # shoulder/upper sleeve and every pixel below the hem remain intact.
        draw = ImageDraw.Draw(body)
        for y in range(20, 25):
            for x in range(8, 11):
                body.putpixel((x, y), (0, 0, 0, 0))
            draw.point((10, y), fill=OUTLINE)
            draw.point((11, y), fill=TEAL)
        draw = ImageDraw.Draw(arm)
        draw.line([elbow, (px, py)], fill=OUTLINE, width=3)
        draw.line([elbow, (px, py)], fill=CREAM, width=2)
        draw.point((px, py), fill=SKIN)
        if angle < 40:
            draw.point((px+1, py-1), fill=SKIN)
    draw = ImageDraw.Draw(energy)
    effects = {
        1: [(0, 0, '#e2f9ff')],
        2: [(0, 0, '#e2f9ff'), (0, -1, '#67cfff'), (1, 0, '#67cfff'),
            (0, 1, '#3689d6'), (-1, 0, '#67cfff')],
        3: [(-1, -1, '#3689d6'), (1, 0, '#67cfff')],
        4: [(1, 1, '#3689d6')],
    }
    for dx, dy, color in effects.get(energy_level, []):
        draw.point((px+3+dx, py-2+dy), fill=color)
    return {'body': body, 'casting_arm': arm, 'energy': energy}, {
        'shoulder': list(shoulder), 'elbow': list(elbow), 'wrist': list(wrist)}


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    idle = Image.open(SOURCE).convert('RGBA')
    idle.save(OUT/'source_body.png')
    for obsolete in ['water.png', 'opening_gate.png', 'working_arm.png', 'head.png']:
        (OUT/obsolete).unlink(missing_ok=True)
    columns = max(len(frames) for _, _, frames in TIMELINE)
    sheet_size = (columns*SIZE[0], len(TIMELINE)*SIZE[1])
    sheet = Image.new('RGBA', sheet_size)
    layer_sheets = {name: Image.new('RGBA', sheet_size) for name in LAYER_ORDER}
    animations = {}
    source_head = idle.crop((0, 0, 24, 14)).tobytes()
    source_legs = idle.crop((0, 25, 24, 36)).tobytes()
    for row, (name, duration, frames) in enumerate(TIMELINE):
        records = []
        for column, (angle, energy_level) in enumerate(frames):
            layers, joints = native_layers(idle, angle, energy_level)
            native = Image.new('RGBA', SOURCE_SIZE)
            for layer_name in LAYER_ORDER:
                native.alpha_composite(layers[layer_name])
            # Check actual art against the approved source, not just landmarks.
            assert native.crop((0, 0, 24, 14)).tobytes() == source_head
            assert native.crop((0, 25, 24, 36)).tobytes() == source_legs
            assert set(native.getchannel('A').tobytes()) <= {0, 255}
            if angle == 90:
                assert native.tobytes() == idle.tobytes()
            rect = [column*SIZE[0], row*SIZE[1], *SIZE]
            canvas = Image.new('RGBA', SIZE)
            canvas.alpha_composite(native, OFFSET)
            sheet.alpha_composite(canvas, rect[:2])
            for layer_name in LAYER_ORDER:
                layer_canvas = Image.new('RGBA', SIZE)
                layer_canvas.alpha_composite(layers[layer_name], OFFSET)
                layer_sheets[layer_name].alpha_composite(layer_canvas, rect[:2])
            canvas_joints = {joint: [xy[0]+OFFSET[0], xy[1]+OFFSET[1]]
                             for joint, xy in joints.items()}
            records.append({'rect': rect, 'angle_degrees': angle,
                            'energy_level': energy_level,
                            'casting_hand': [round(joints['wrist'][0])+OFFSET[0],
                                             round(joints['wrist'][1])+OFFSET[1]],
                            'joints': {'casting': [canvas_joints['shoulder'],
                                                  canvas_joints['elbow'],
                                                  canvas_joints['wrist']]}})
        animations[name] = {'duration_ms': duration, 'frames': records}
    sheet.save(OUT/'poses.png')
    for name, layer in layer_sheets.items():
        layer.save(OUT/(name+'.png'))
    (OUT/'animation.json').write_text(json.dumps({
        'canvas': list(SIZE), 'anchor': list(ANCHOR),
        'source_canvas': list(SOURCE_SIZE), 'source_offset': list(OFFSET),
        'source_body': 'source_body.png',
        'source_idle_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'layer_order': LAYER_ORDER, 'arm_lengths': [4, 4],
        'preserved_source_regions': {'head': [0, 0, 24, 14],
                                     'lower_body': [0, 25, 24, 36]},
        'outcome': 'failed', 'water_displacement': False,
        'sequence': [name for name, _, _ in TIMELINE],
        'animations': animations,
    }, indent=2)+'\n')


if __name__ == '__main__':
    build()
