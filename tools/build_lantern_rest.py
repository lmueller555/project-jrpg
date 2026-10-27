"""Build grounded carry and paper-work art for MQ04's home/sanctuary visit.

Approved Liam heads and walking legs are read-only. The small empty tower is
supported by its base beside him, leaving his face visible and its bottom clear
of the floor. Each walk frame retains the source stride and one-pixel bob.
"""
from pathlib import Path
import hashlib
import json
import math
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_lantern_quest import frame, drawing_image, joints

OUT = ROOT/'assets/story/lantern'
SIZE = (40, 48)
OFFSET = (8, 8)
ANCHOR = (20, 38)
DIRECTIONS = ('front', 'left', 'right', 'back')
OUTLINE = '#2c2523'
SLEEVE = '#b38c37'
SKIN = '#e6b881'
PAPER = '#e4d5ad'
INK = '#6a796e'


def save(path, image):
    target = OUT/path;target.parent.mkdir(parents=True, exist_ok=True)
    assert set(image.getchannel('A').tobytes()) <= {0, 255}, path
    temp = target.with_name(target.name+'.tmp');image.save(temp, format='PNG');temp.replace(target)
    return target.relative_to(ROOT).as_posix()


def write(path, value):
    target = OUT/path;target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name+'.tmp')
    temp.write_text(json.dumps(value, indent=2)+'\n');temp.replace(target)
    return target.relative_to(ROOT).as_posix()


def load(path):return Image.open(ROOT/path).convert('RGBA')


def arm(direction, wrist, dy=0):
    shoulder = (10., 23.+dy) if direction == 'left' else (14., (22. if direction in ('front', 'back') else 23.)+dy)
    points = joints(shoulder, wrist, 3.2, 3.2, -1 if direction == 'left' else 1)
    rounded = [tuple(round(v) for v in p) for p in points]
    image = Image.new('RGBA', (24, 36));d = ImageDraw.Draw(image)
    d.line(rounded, fill=OUTLINE, width=2);d.line(rounded[:2], fill=SLEEVE)
    d.line(rounded[1:], fill=SKIN);d.point(rounded[-1], fill='#f0c594')
    return image, points


def bare_body(source, direction, walking=None):
    if walking is None:
        body = source.copy()
        # Retain the complete torso and opposite arm; remove only the hanging
        # outside sleeve/hand which is replaced by the compact supporting arm.
        outside = range(0, 10) if direction == 'left' else range(14 if direction == 'right' else 15, 24)
        for y in range(21, 28):
            for x in outside:body.putpixel((x, y), (0, 0, 0, 0))
    else:
        body = Image.new('RGBA', (24, 36))
        carried = 'left_arm' if direction == 'left' else 'right_arm'
        for path in walking['layers_from_repo_root']:
            if path.endswith('_'+carried+'.png'):continue
            body.alpha_composite(load(path))
    return body


def registered_pose(source, source_path, direction, wrist, *, walking=None, carried=False, food=False, pencil=False, dy=0, frame_angle=0):
    body = bare_body(source, direction, walking)
    working, points = arm(direction, wrist, dy);body.alpha_composite(working)
    # Preserve the entire head and lower body, not just opaque matching pixels.
    body.paste(source.crop((0, 0, 24, 21)), (0, 0))
    body.paste(source.crop((0, 28, 24, 36)), (0, 28))
    assert body.crop((0, 0, 24, 21)).tobytes() == source.crop((0, 0, 24, 21)).tobytes()
    assert body.crop((0, 28, 24, 36)).tobytes() == source.crop((0, 28, 24, 36)).tobytes()
    padded = Image.new('RGBA', SIZE);padded.alpha_composite(body, OFFSET)
    item = Image.new('RGBA', SIZE);extras = Image.new('RGBA', SIZE)
    hand = tuple(round(v)+8 for v in wrist)
    if carried:
        # One palm supports the base. This is the same tower asset that was on
        # Mira's table, without scaling its shape or dangling it through feet.
        support = (7, 15) if direction == 'left' else (3, 15)
        lattice = frame()
        if frame_angle:
            lattice = lattice.rotate(frame_angle, resample=Image.Resampling.NEAREST, expand=True)
            radians = math.radians(frame_angle)
            dx, dy_support = support[0]-5, support[1]-8
            support = (round(math.cos(radians)*dx+math.sin(radians)*dy_support+(lattice.width-1)/2),
                       round(-math.sin(radians)*dx+math.cos(radians)*dy_support+(lattice.height-1)/2))
            if frame_angle == 90:
                lattice = lattice.resize((17, 8), Image.Resampling.NEAREST)
                support = (support[0], round(support[1]*8/11))
        item.alpha_composite(lattice, (hand[0]-support[0], hand[1]-support[1]))
    if food:
        d = ImageDraw.Draw(extras);d.rectangle((hand[0]-1, hand[1]-2, hand[0]+1, hand[1]), fill='#b88a51')
        d.line((hand[0]-1, hand[1]-2, hand[0]+1, hand[1]-2), fill='#e6cf97')
    if pencil:
        d = ImageDraw.Draw(extras);d.line((hand[0]+1, hand[1], hand[0]+4, hand[1]-1), fill='#9b774a')
        d.point((hand[0]+4, hand[1]-1), fill=INK)
    canvas = item.copy();canvas.alpha_composite(padded);canvas.alpha_composite(extras)
    # Keep the grip in front of its supported lattice and tools.
    ImageDraw.Draw(canvas).point(hand, fill='#f0c594')
    source_padded = Image.new('RGBA', SIZE);source_padded.alpha_composite(source, OFFSET)
    frame_box = item.getbbox()
    feet = max(y for y in range(28, 36) for x in range(24) if source.getpixel((x, y))[3])+8
    clearance = feet-(frame_box[3]-1) if frame_box else None
    if carried:assert clearance >= 1, (direction, clearance)
    record = {'duration_ms': 140 if walking else 180, 'source_path': source_path,
              'source_sha256': hashlib.sha256((ROOT/source_path).read_bytes()).hexdigest(),
              'native_offset': list(OFFSET), 'preserved_regions': [[0, 0, 24, 21], [0, 28, 24, 8]],
              'joints': points, 'hand': list(hand), 'native_wrist': list(wrist),
              'holds_frame': carried, 'frame_bbox': list(frame_box) if frame_box else None,
              'ground_clearance_pixels': clearance, 'frame_angle': frame_angle}
    return canvas, padded, item, extras, source_padded, record


def build_poses():
    sheet = Image.new('RGBA', (200, 384))
    layers = {name: Image.new('RGBA', sheet.size) for name in ('body', 'frame', 'extras', 'source')}
    carry = {};actions = {}
    def add(row, column, *args, **kwargs):
        canvas, body, item, extras, source, record = registered_pose(*args, **kwargs)
        rect = [column*40, row*48, 40, 48];sheet.alpha_composite(canvas, rect[:2])
        for name, image in (('body', body), ('frame', item), ('extras', extras), ('source', source)):
            layers[name].alpha_composite(image, rect[:2])
        return {'rect': rect, **record}
    for row, direction in enumerate(DIRECTIONS):
        path = f'assets/characters/liam/idle_{direction}.png';idle = load(path)
        wrist = (5., 25.) if direction == 'left' else (18., 25.)
        idle_record = add(row, 0, idle, path, direction, wrist, carried=True)
        folder = f'assets/characters/liam/walk_{direction}'
        meta = json.loads((ROOT/folder/'animation.json').read_text())
        walking = []
        for i, step in enumerate(meta['frames']):
            dy = step['upper_body_offset'][1];path = folder+'/'+step['file']
            record = add(row, i+1, load(path), path, direction, (wrist[0], wrist[1]+dy), walking=step, carried=True, dy=dy)
            record['duration_ms'] = step['duration_ms'];record['source_walk_frame'] = i
            walking.append(record)
        carry[direction] = {'idle': idle_record, 'walk': walking}
    specs = {
        'pickup': ('right', [(16., 24.), (17., 21.), (18., 19.), (17., 22.), (18., 25.)]),
        'place': ('left', [(5.2, 25.), (5.2, 25.5), (5.2, 26.), (5.2, 26.5), (5.2, 27.)]),
        'work': ('right', [(18., 24.), (20., 24.), (20., 23.), (20., 24.), (18., 24.)]),
        'snack': ('right', [(16., 24.), (16., 22.), (16., 21.), (16., 22.), (16., 24.)]),
    }
    for row, (kind, (direction, wrists)) in enumerate(specs.items(), 4):
        path = f'assets/characters/liam/idle_{direction}.png';source = load(path)
        records = []
        for i, wrist in enumerate(wrists):
            records.append(add(row, i, source, path, direction, wrist,
                               carried=kind == 'place', food=kind == 'snack', pencil=kind == 'work',
                               frame_angle=(0, 22.5, 45, 67.5, 90)[i] if kind == 'place' else 0))
        actions[kind] = records
    path = save('rest_poses/liam.png', sheet)
    layer_paths = {name: save(f'rest_poses/liam_{name}.png', image) for name, image in layers.items()}
    return write('rest_poses/liam.json', {
        'canvas': list(SIZE), 'draw_anchor': list(ANCHOR), 'native_offset': list(OFFSET),
        'source_canvas': [24, 36], 'sheet': path, 'body_sheet': layer_paths['body'],
        'frame_sheet': layer_paths['frame'], 'source_sheet': layer_paths['source'], 'layers': layer_paths,
        'carry': carry, 'actions': actions, 'arm_lengths': [3.2, 3.2],
        'preserved_regions': [[0, 0, 24, 21], [0, 28, 24, 8]],
        'source_head_legs_preserved': True, 'frame_source': 'assets/story/lantern/props/frame.png',
        'carry_style': 'Palm under the base beside the body, with the face and all feet unobscured.',
        'pickup_has_held_frame': False, 'place_has_held_frame': True,
        'action_facing': {'pickup': 'right', 'place': 'left', 'work': 'right', 'snack': 'right'},
        'world_contacts': {'pickup': [668, 489], 'place': [315, 231], 'work': [270, 228]},
        'work_foreground_sort_y': 271,
    })


def papers(state):
    image = Image.new('RGBA', (23, 15));d = ImageDraw.Draw(image)
    d.polygon([(1, 1), (19, 0), (22, 12), (3, 14)], fill=PAPER)
    d.line((4, 3, 16, 3), fill='#cfbf94')
    steps = [(5, 11), (5, 9), (8, 9), (8, 7), (11, 7), (11, 5), (14, 5)]
    if state == 'smudged':
        d.line(steps+[(18, 4)], fill=INK);d.line((14, 4, 19, 7), fill='#b1a17d', width=2)
    elif state == 'revised':
        d.line([(5, 11), (5, 8), (9, 8), (9, 5), (13, 5)], fill=INK)
    else:d.line(steps, fill=INK)
    return image


def snack(state):
    image = Image.new('RGBA', (18, 15));d = ImageDraw.Draw(image)
    d.ellipse((1, 6, 13, 12), fill='#aeb6a3', outline='#626c60')
    d.ellipse((3, 7, 11, 10), fill='#cbd0b8')
    if state != 'used':
        d.rectangle((4, 5, 10, 8), fill='#b88a51');d.line((5, 5, 9, 5), fill='#e6cf97')
    d.rectangle((12, 1, 15, 7), fill='#8b9a88');d.line((12, 1, 15, 1), fill='#c4ceb7')
    d.line((16, 2, 17, 3, 17, 5, 16, 6), fill='#8b9a88')
    return image


def build():
    pose = build_poses()
    empty = save('rest_props/workshop_collected.png', Image.new('RGBA', (64, 56)))
    resting = frame().transpose(Image.Transpose.ROTATE_90).resize((17, 8), Image.Resampling.NEAREST)
    frame_path = save('rest_props/home_frame.png', resting)
    drawing = save('rest_props/home_drawing.png', drawing_image().resize((12, 8), Image.Resampling.NEAREST))
    paper_paths = {state: save(f'rest_props/paper_{state}.png', papers(state)) for state in ('clean', 'smudged', 'revised')}
    snacks = {state: save(f'rest_props/snack_{state}.png', snack(state)) for state in ('ready', 'used')}
    props = [
        {'id': 'home_frame', 'scene': 'liam_house', 'position': [300, 229], 'sort_y': 271, 'states': {'ready': frame_path}},
        {'id': 'home_drawing', 'scene': 'liam_house', 'position': [288, 238], 'sort_y': 271, 'states': {'ready': drawing}},
        {'id': 'home_papers', 'scene': 'liam_house', 'position': [270, 226], 'sort_y': 271, 'states': paper_paths},
        {'id': 'home_snack', 'scene': 'liam_house', 'position': [270, 230], 'sort_y': 271, 'states': snacks},
    ]
    write('rest_art.json', {'poses': {'liam': pose}, 'props': props, 'workshop_collected': empty,
                            'frame_source': 'assets/story/lantern/props/frame.png', 'frame_is_lit': False,
                            'final_covering_attached': False})
    write('rest_layout.json', {
        'collection': [623, 512], 'workshop': [623, 512],
        'collection_liam': [646, 500], 'pickup_liam': [662, 500],
        'collection_tomas': [710, 516], 'collection_mira': [682, 500],
        'home': [320, 216], 'paper': [320, 216], 'home_liam': [262, 234],
        'work_liam': [262, 234], 'place_liam': [322, 234], 'home_tomas': [330, 274], 'home_father': [366, 234],
        'frame_home': [300, 229], 'drawing_home': [288, 238], 'paper_home': [270, 226],
        'sanctuary': [160, 230], 'sanctuary_liam': [180, 210],
        'sanctuary_tomas': [206, 220], 'sanctuary_serene': [224, 228],
        'home_scene': 'liam_house', 'sanctuary_scene': 'sanctuary_hall',
        'home_entry': [252, 294], 'home_exit': [252, 306],
        'sanctuary_entry': [208, 294], 'sanctuary_exit': [208, 306],
        'pickup_hand': [668, 489], 'place_hand': [315, 231], 'work_hand': [270, 228],
    })
    # Developer review only. This board preserves native pixels at integer scale.
    folder = ROOT/'work/lantern-rest-art';folder.mkdir(parents=True, exist_ok=True)
    sheet = Image.open(ROOT/'assets/story/lantern/rest_poses/liam.png').convert('RGBA')
    board = Image.new('RGB', (1000, 700), '#e8edf2');d = ImageDraw.Draw(board)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 15)
    meta = json.loads((OUT/'rest_poses/liam.json').read_text())
    for row, direction in enumerate(DIRECTIONS):
        d.text((8, row*100+8), direction, fill='#243529', font=font)
        records = [meta['carry'][direction]['idle'], *meta['carry'][direction]['walk']]
        for column, rec in enumerate(records):
            x, y, w, h = rec['rect'];cell = sheet.crop((x, y, x+w, y+h))
            board.paste(cell.resize((80, 96), Image.Resampling.NEAREST), (100+column*125, row*100), cell.resize((80, 96), Image.Resampling.NEAREST))
    for row, kind in enumerate(('pickup', 'place', 'work', 'snack')):
        y = 405+(row//2)*140;x = (row%2)*500
        d.text((x+8, y), kind, fill='#243529', font=font)
        for column, rec in enumerate(meta['actions'][kind]):
            xx, yy, w, h = rec['rect'];cell = sheet.crop((xx, yy, xx+w, yy+h)).resize((80, 96), Image.Resampling.NEAREST)
            board.paste(cell, (x+column*96, y+24), cell)
    board.save(folder/'pose_board.png')
    print('Built PR3 carry/work art:', len(props), 'home props; four carry directions; four actions.')


if __name__ == '__main__':build()
