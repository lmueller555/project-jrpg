"""Build the papered, unlit version of Liam's existing tower lantern.

Every body cell is copied from the approved PR3 carrying/work atlas. Only the
separate object layer changes; the original head, legs, feet and arm joints are
retained. Covering is fitted behind the existing lattice, never over its handle,
roof point or ventilation gap.
"""
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_lantern_quest import frame

OUT = ROOT/'assets/story/lantern'
SIZE = (40, 48)
ANCHOR = (20, 38)
DIRECTIONS = ('front', 'left', 'right', 'back')
PAPER = '#e4d5ad'
PAPER_LIGHT = '#f0e3bc'
INK = '#61766e'
WINDOW = '#4e665e'


def load(path):return Image.open(ROOT/path).convert('RGBA')


def digest(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()


def save(path, image):
    target = OUT/path;target.parent.mkdir(parents=True, exist_ok=True)
    assert set(image.getchannel('A').tobytes()) <= {0, 255}, path
    temporary = target.with_name(target.name+'.tmp')
    image.save(temporary, format='PNG');temporary.replace(target)
    return target.relative_to(ROOT).as_posix()


def write(path, value):
    target = OUT/path;target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name+'.tmp')
    temporary.write_text(json.dumps(value, indent=2)+'\n');temporary.replace(target)
    return target.relative_to(ROOT).as_posix()


def papered_frame(partial=False):
    """The same eleven-by-seventeen tower, with a hand-drawn paper face."""
    lattice = frame()
    image = Image.new('RGBA', lattice.size)
    d = ImageDraw.Draw(image)
    d.rectangle((3, 6, 5 if partial else 7, 13), fill=PAPER)
    d.line((3, 6, 5 if partial else 7, 6), fill=PAPER_LIGHT)
    # Fewer, larger stairs leave the small window visible. One step is
    # deliberately a little uneven, as Liam notices in the closing scene.
    d.line([(3, 13), (4, 13), (4, 12), (5, 12), (5, 11)], fill=INK)
    if not partial:
        d.rectangle((6, 7, 7, 8), fill=WINDOW)
        d.point((6, 7), fill='#8d9d83')
    image.alpha_composite(lattice)
    for y in range(lattice.height):
        for x in range(lattice.width):
            if lattice.getpixel((x, y))[3]:
                assert image.getpixel((x, y)) == lattice.getpixel((x, y)), (x, y)
    # The existing handle/crown/vent stays exactly registered and unpapered.
    assert image.crop((0, 0, 11, 6)).tobytes() == lattice.crop((0, 0, 11, 6)).tobytes()
    return image


def held_item(record, direction, item):
    image = Image.new('RGBA', SIZE)
    if not record.get('holds_frame'):return image
    hand = tuple(record['hand'])
    support = (7, 15) if direction == 'left' else (3, 15)
    angle = record.get('frame_angle', 0)
    if angle:
        item = item.rotate(angle, resample=Image.Resampling.NEAREST, expand=True)
        radians = math.radians(angle)
        dx, dy = support[0]-5, support[1]-8
        support = (round(math.cos(radians)*dx+math.sin(radians)*dy+(item.width-1)/2),
                   round(-math.sin(radians)*dx+math.cos(radians)*dy+(item.height-1)/2))
        if angle == 90:
            item = item.resize((17, 8), Image.Resampling.NEAREST)
            support = (support[0], round(support[1]*8/11))
    image.alpha_composite(item, (hand[0]-support[0], hand[1]-support[1]))
    return image


def build_poses():
    previous = json.loads((OUT/'rest_poses/liam.json').read_text())
    old = {key: load(path) for key, path in previous['layers'].items()}
    sheet = Image.new('RGBA', (200, 384))
    layers = {key: Image.new('RGBA', sheet.size) for key in ('body', 'frame', 'extras', 'source')}
    carry = {};actions = {}

    def cell(record, row, column, direction, *, held=None, extras=True):
        original = deepcopy(record)
        source_rect = tuple(original['rect']);x, y, width, height = source_rect
        box = (x, y, x+width, y+height)
        body = old['body'].crop(box);source = old['source'].crop(box)
        tools = old['extras'].crop(box) if extras else Image.new('RGBA', SIZE)
        if held is not None:original['holds_frame'] = held
        if original['holds_frame']:
            # The transformed bare frame must exactly reproduce PR3's item
            # registration before replacing it with the papered version.
            reconstructed = held_item(original, direction, frame())
            assert reconstructed.tobytes() == old['frame'].crop(box).tobytes(), source_rect
        item = held_item(original, direction, papered_frame())
        composed = item.copy();composed.alpha_composite(body);composed.alpha_composite(tools)
        ImageDraw.Draw(composed).point(tuple(original['hand']), fill='#f0c594')
        rect = [column*40, row*48, 40, 48]
        sheet.alpha_composite(composed, rect[:2])
        for key, value in (('body', body), ('frame', item), ('extras', tools), ('source', source)):
            layers[key].alpha_composite(value, rect[:2])
        for xx, yy, ww, hh in previous['preserved_regions']:
            region = (xx+8, yy+8, xx+ww+8, yy+hh+8)
            assert body.crop(region).tobytes() == source.crop(region).tobytes(), (row, column, region)
        frame_box = item.getbbox()
        clearance = original.get('ground_clearance_pixels') if original['holds_frame'] else None
        if original['holds_frame']:assert clearance is not None and clearance>=1
        original.update(rect=rect, source_rest_rect=list(source_rect),
                        frame_bbox=list(frame_box) if frame_box else None,
                        ground_clearance_pixels=clearance, covering_attached=bool(original['holds_frame']),
                        frame_is_lit=False)
        return original

    for row, direction in enumerate(DIRECTIONS):
        spec = previous['carry'][direction]
        carry[direction] = {'idle': cell(spec['idle'], row, 0, direction),
                            'walk': [cell(rec, row, i+1, direction) for i, rec in enumerate(spec['walk'])]}
    for row, kind in enumerate(('prepare', 'cover', 'pickup', 'place'), 4):
        refs = previous['actions']['work'] if kind in ('prepare', 'cover') else previous['actions']['place']
        if kind == 'pickup':refs = list(reversed(refs))
        direction = 'right' if kind in ('prepare', 'cover') else 'left'
        actions[kind] = [cell(rec, row, i, direction, held=False if kind == 'pickup' else None,
                              extras=kind == 'prepare') for i, rec in enumerate(refs)]
    path = save('finish_poses/liam.png', sheet)
    paths = {key: save(f'finish_poses/liam_{key}.png', image) for key, image in layers.items()}
    return write('finish_poses/liam.json', {
        'canvas': list(SIZE), 'draw_anchor': list(ANCHOR), 'native_offset': [8, 8],
        'source_canvas': [24, 36], 'sheet': path, 'body_sheet': paths['body'],
        'frame_sheet': paths['frame'], 'source_sheet': paths['source'], 'layers': paths,
        'carry': carry, 'actions': actions, 'arm_lengths': previous['arm_lengths'],
        'preserved_regions': previous['preserved_regions'], 'source_head_legs_preserved': True,
        'body_source': 'assets/story/lantern/rest_poses/liam_body.png',
        'body_source_sha256': digest('assets/story/lantern/rest_poses/liam_body.png'),
        'source_rest_pose_metadata': 'assets/story/lantern/rest_poses/liam.json',
        'source_rest_pose_sha256': digest('assets/story/lantern/rest_poses/liam.json'),
        'bare_frame_source': 'assets/story/lantern/props/frame.png',
        'bare_frame_sha256': digest('assets/story/lantern/props/frame.png'),
        'covered_frame_source': 'assets/story/lantern/finish_props/covered_frame.png',
        'covering_attached': True, 'frame_is_lit': False,
        'pickup_has_held_frame': False, 'place_has_held_frame': True,
        'action_facing': {'prepare': 'right', 'cover': 'right', 'pickup': 'left', 'place': 'left'},
        'world_contacts': {'pickup': [315, 231], 'place': [315, 231], 'work': [270, 228]},
        'carry_style': 'Exact PR3 supporting body/gait, with only its separate frame covered in paper.',
    })


def panel(final=False):
    image = Image.new('RGBA', (23, 15));d = ImageDraw.Draw(image)
    d.polygon([(1, 1), (19, 0), (22, 12), (3, 14)], fill=PAPER)
    if final:
        d.line([(5, 11), (5, 8), (9, 8), (9, 5), (12, 5)], fill=INK)
        d.rectangle((13, 4, 16, 7), fill=WINDOW)
        d.line((14, 4, 16, 4), fill='#8d9d83')
    else:
        d.line([(5, 11), (5, 8), (9, 8), (9, 5), (13, 5)], fill='#a29a7d')
        d.rectangle((14, 4, 17, 7), outline='#a29a7d')
    return image


def build():
    covered = papered_frame();partial = papered_frame(True)
    upright = save('finish_props/covered_frame.png', covered)
    partial_path = save('finish_props/home_partial.png', partial.transpose(Image.Transpose.ROTATE_90).resize((17, 8), Image.Resampling.NEAREST))
    finished = save('finish_props/home_finished.png', covered.transpose(Image.Transpose.ROTATE_90).resize((17, 8), Image.Resampling.NEAREST))
    panel_paths = {state: save(f'finish_props/panel_{state}.png', panel(state == 'final')) for state in ('draft', 'final')}
    empty = save('finish_props/panel_empty.png', Image.new('RGBA', (23, 15)))
    pose = build_poses()
    props = [
        {'id': 'home_lantern', 'scene': 'liam_house', 'position': [300, 229], 'sort_y': 271,
         'states': {'bare': 'assets/story/lantern/rest_props/home_frame.png',
                    'panel': 'assets/story/lantern/rest_props/home_frame.png',
                    'partial': partial_path, 'finished': finished}},
        {'id': 'final_panel', 'scene': 'liam_house', 'position': [270, 226], 'sort_y': 271,
         'states': {'draft': panel_paths['draft'], 'final': panel_paths['final'], 'empty': empty}},
    ]
    write('finish_art.json', {'poses': {'liam': pose}, 'props': props, 'covered_frame': upright,
                              'frame_source': 'assets/story/lantern/props/frame.png',
                              'frame_is_lit': False, 'final_covering_attached': True,
                              'keeps_handle_roof_vent_and_lattice': True,
                              'old_props_policy': 'Replace rest home_frame with home_lantern; leave original drawing, hide practice only while final_panel is displayed.'})
    write('finish_layout.json', {
        'invitation': [160, 230], 'invitation_liam': [180, 210], 'invitation_tomas': [206, 220],
        'home': [320, 216], 'home_liam': [262, 234], 'home_tomas': [330, 274],
        'work_liam': [262, 234], 'pickup_liam': [322, 234], 'place_liam': [322, 234],
        'home_father': [366, 234], 'frame_home': [300, 229], 'paper_home': [270, 226],
        'school': [254, 302], 'school_liam': [318, 246], 'school_tomas': [228, 270],
        'school_mother': [266, 246],
        'home_scene': 'liam_house', 'school_scene': 'school', 'invitation_scene': 'sanctuary_hall',
        'home_entry': [252, 294], 'home_exit': [252, 306],
        'school_entry': [216, 342], 'school_exit': [216, 354],
        'sanctuary_entry': [208, 294], 'sanctuary_exit': [208, 306],
        'pickup_hand': [315, 231], 'place_hand': [315, 231], 'work_hand': [270, 228],
        'tomas_after': [252, 230], 'serene_after': [224, 228],
    })
    review_board()
    print('Built PR4 covered lantern:', len(props), 'props; unchanged PR3 carry bodies; four directions.')


def review_board():
    folder = ROOT/'work/lantern-finish-art';folder.mkdir(parents=True, exist_ok=True)
    sheet = load('assets/story/lantern/finish_poses/liam.png')
    meta = json.loads((OUT/'finish_poses/liam.json').read_text())
    board = Image.new('RGB', (1000, 800), '#e8edf2');d = ImageDraw.Draw(board)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 15)
    for row, direction in enumerate(DIRECTIONS):
        d.text((8, row*100+8), direction, fill='#243529', font=font)
        records = [meta['carry'][direction]['idle'], *meta['carry'][direction]['walk']]
        for column, rec in enumerate(records):
            x, y, width, height = rec['rect'];cell = sheet.crop((x, y, x+width, y+height)).resize((80, 96), Image.Resampling.NEAREST)
            board.paste(cell, (100+column*125, row*100), cell)
    for row, kind in enumerate(('prepare', 'cover', 'pickup', 'place')):
        yy = 405+(row//2)*140;xx = (row%2)*500
        d.text((xx+8, yy), kind, fill='#243529', font=font)
        for column, rec in enumerate(meta['actions'][kind]):
            x, y, width, height = rec['rect'];cell = sheet.crop((x, y, x+width, y+height)).resize((80, 96), Image.Resampling.NEAREST)
            board.paste(cell, (xx+column*96, yy+24), cell)
    for column, item in enumerate((frame(), papered_frame(True), papered_frame())):
        enlarged = item.resize((44, 68), Image.Resampling.NEAREST)
        board.paste(enlarged, (720+column*85, 715), enlarged)
    d.text((8, 735), 'The same tower: bare, partly covered, finished and unlit.', fill='#243529', font=font)
    board.save(folder/'pose_board.png')


if __name__ == '__main__':build()
