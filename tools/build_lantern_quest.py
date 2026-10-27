"""Rebuild MQ04's small, unlit craft props and body-registered work poses.

The approved idle head, hips, legs and boots stay at their normal coordinates.
Only a single working arm changes. Liam's short lift is two native pixels;
the frame hangs from his hand rather than requiring an overhead reach.
"""
from pathlib import Path
import hashlib
import json
import math

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'assets/story/lantern'
ART = 'assets/story/lantern/'
WOOD_DARK = '#54452f'
WOOD = '#9b774a'
WOOD_LIGHT = '#c3a16b'
OUTLINE = '#2c2523'
PAPER = '#e4d5ad'
INK = '#6a796e'
SIZE = (40, 48)
OFFSET = (8, 8)
ANCHOR = (20, 38)


def save(name, image):
    path = OUT/name
    path.parent.mkdir(parents=True, exist_ok=True)
    assert set(image.getchannel('A').tobytes()) <= {0, 255}, name
    temporary = path.with_name(path.name+'.tmp')
    image.save(temporary, format='PNG')
    temporary.replace(path)
    return path.relative_to(ROOT).as_posix()


def json_file(name, value):
    path = OUT/name
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(value, indent=2)+'\n')
    temporary.replace(path)
    return path.relative_to(ROOT).as_posix()


def frame():
    """A light lattice tower, with a vented crown and an empty light socket."""
    image = Image.new('RGBA', (11, 17))
    d = ImageDraw.Draw(image)
    d.line([(3, 3), (3, 1), (4, 0), (6, 0), (7, 1), (7, 3)], fill=WOOD_DARK)
    d.line([(4, 3), (4, 1), (6, 1), (6, 3)], fill=WOOD_LIGHT)
    d.line((2, 4, 8, 4), fill=WOOD_DARK)
    d.line((3, 3, 3, 5), fill=WOOD_LIGHT)
    d.line((7, 3, 7, 5), fill=WOOD_LIGHT)
    for x in (2, 8):
        d.line((x, 5, x, 15), fill=WOOD_DARK, width=2)
        d.line((x, 5, x, 14), fill=WOOD_LIGHT)
    d.line((3, 5, 7, 5), fill=WOOD_LIGHT)
    d.line((3, 10, 7, 10), fill=WOOD_DARK)
    d.line((3, 15, 7, 15), fill=WOOD_DARK, width=2)
    d.line((3, 14, 7, 14), fill=WOOD_LIGHT)
    # This is an empty socket, never a lit flame or magical glow.
    d.line((4, 13, 6, 13), fill='#7c8278')
    return image


def table():
    image = Image.new('RGBA', (64, 28))
    d = ImageDraw.Draw(image)
    d.polygon([(0, 6), (58, 6), (63, 13), (0, 13)], fill=WOOD_DARK)
    d.polygon([(1, 7), (57, 7), (61, 12), (1, 12)], fill=WOOD)
    for y in (8, 10):
        d.line((4, y, 58, y), fill=WOOD_LIGHT)
    d.rectangle((1, 13, 62, 16), fill=WOOD_DARK)
    d.line((3, 13, 60, 13), fill=WOOD_LIGHT)
    for x in (7, 53):
        d.rectangle((x, 16, x+3, 27), fill=WOOD_DARK)
        d.line((x, 17, x, 25), fill=WOOD)
    d.line((9, 23, 55, 23), fill=WOOD_DARK, width=2)
    return image


def drawing_image():
    image = Image.new('RGBA', (24, 15))
    d = ImageDraw.Draw(image)
    d.polygon([(0, 1), (20, 0), (23, 12), (3, 14)], fill=PAPER)
    d.line([(8, 11), (7, 5), (6, 5), (6, 3), (8, 3), (8, 5), (12, 4),
            (12, 2), (14, 2), (14, 4), (15, 10), (8, 11)], fill=INK)
    d.line((9, 7, 12, 7), fill=INK)
    d.line((18, 7, 20, 9), fill='#b58755')
    return image


def craft_surface(state):
    """Overlay registered above the trestle, without moving its furniture."""
    image = Image.new('RGBA', (64, 56))
    d = ImageDraw.Draw(image)
    image.alpha_composite(drawing_image(), (5, 23))
    if state != 'drawing':
        for x, y, length in ((29, 26, 16), (32, 29, 19), (30, 31, 15)):
            d.line((x, y, x+length, y), fill=WOOD_DARK, width=2)
            d.line((x, y, x+length-1, y), fill=WOOD_LIGHT)
        d.ellipse((51, 24, 59, 30), fill='#af9d75', outline=WOOD_DARK)
        d.ellipse((54, 26, 57, 28), fill='#837b5e')
    if state == 'test':
        d.line([(27, 23), (37, 17), (48, 23), (37, 29), (27, 23)], fill=WOOD_DARK, width=2)
        d.line((37, 17, 37, 29), fill=WOOD_LIGHT)
    if state == 'partial':
        d.line([(29, 23), (40, 18), (52, 24), (40, 30), (29, 23)], fill=WOOD_DARK, width=2)
        for x, y in ((29, 23), (40, 18), (52, 24)):
            d.line((x, y, x, y-9), fill=WOOD_LIGHT)
        d.line([(29, 14), (40, 9), (52, 15)], fill=WOOD_DARK)
    if state == 'ready':
        # After the balance check Mira rests the light frame flat on the table.
        # The same tower is foreshortened into the tabletop's existing plane.
        resting = frame().transpose(Image.Transpose.ROTATE_90)
        resting = resting.resize((17, 8), Image.Resampling.NEAREST)
        image.alpha_composite(resting, (31, 23))
    shifted = Image.new('RGBA', image.size)
    shifted.alpha_composite(image, (0, 6))
    image = shifted
    if state == 'frame':
        # The newly assembled tower is set down in front of the workbench for
        # Liam's lift. Its handle is at his reachable waist/upper-arm height.
        image.alpha_composite(frame(), (10, 35))
    return image


def joints(shoulder, wrist, upper, forearm, bend):
    dx, dy = wrist[0]-shoulder[0], wrist[1]-shoulder[1]
    distance = math.hypot(dx, dy)
    assert abs(upper-forearm) < distance <= upper+forearm, (shoulder, wrist)
    along = (upper*upper-forearm*forearm+distance*distance)/(2*distance)
    height = math.sqrt(max(0, upper*upper-along*along))
    elbow = (shoulder[0]+dx*along/distance+(-dy/distance)*height*bend,
             shoulder[1]+dy*along/distance+(dx/distance)*height*bend)
    return [list(shoulder), list(elbow), list(wrist)]


def working_body(name, wrist):
    direction = 'left' if name == 'mira' else 'right'
    source_path = ROOT/f'assets/characters/{name}/idle_{direction}.png'
    source = Image.open(source_path).convert('RGBA')
    body = source.copy()
    arm = Image.new('RGBA', source.size)
    if name == 'liam':
        shoulder = (14., 23.);lengths = (3.2, 3.2);bend = 1
        for y in range(24, 28):
            for x in range(14, 16):body.putpixel((x, y), (0, 0, 0, 0))
        sleeve = '#b38c37';skin = '#e6b881';head_bottom = 21;lower_top = 28
    elif name == 'mira':
        shoulder = (12., 18.);lengths = (4., 4.);bend = -1
        for y in range(21, 26):
            for x in range(12, 15):body.putpixel((x, y), (0, 0, 0, 0))
        sleeve = '#cf8099';skin = '#edb57d';head_bottom = 16;lower_top = 27
    else:
        # Caelan reaches with the far arm: his near hanging sleeve remains
        # untouched. Its native shoulder at [14,17] reaches the table with
        # ordinary arm lengths; moving the near shoulder would stretch it.
        shoulder = (14., 17.);lengths = (4.5, 4.5);bend = 1
        sleeve = '#fbeed0';skin = '#e8c49d';head_bottom = 14;lower_top = 25
    points = joints(shoulder, wrist, *lengths, bend)
    rounded = [tuple(round(v) for v in p) for p in points]
    d = ImageDraw.Draw(arm)
    d.line(rounded, fill=OUTLINE, width=2 if name == 'liam' else 3)
    d.line(rounded[:2], fill=sleeve)
    d.line(rounded[1:], fill=skin)
    d.point(rounded[-1], fill='#f0c594')
    native = body.copy();native.alpha_composite(arm)
    # Existing head pixels remain byte-identical; reaching through previously
    # transparent pixels outside the head's silhouette is permissible.
    for y in range(head_bottom):
        for x in range(24):
            if source.getpixel((x, y))[3]:
                assert native.getpixel((x, y)) == source.getpixel((x, y)), (name, x, y)
    assert native.crop((0, lower_top, 24, 36)).tobytes() == source.crop((0, lower_top, 24, 36)).tobytes()
    return native, body, arm, points, source, source_path, lower_top, head_bottom


def build_poses(name):
    if name == 'liam':
        work_wrists = [(16., 24.), (17., 22.), (18., 19.), (18., 19.), (17., 22.)]
        lift_wrists = [(17., 20.), (17., 19.), (17., 18.), (17., 18.), (17., 19.), (17., 20.)]
        specs = {'work': work_wrists, 'lift': lift_wrists}
    elif name == 'mira':
        specs = {'work': [(12., 24.), (9., 22.), (6., 18.), (6., 18.), (9., 22.)]}
    else:
        specs = {'work': [(16., 23.), (19., 20.), (22., 18.), (22., 18.), (19., 20.)],
                 'support': [(16., 23.), (19., 22.), (21., 21.), (21., 21.)]}
    width = max(map(len, specs.values()))*SIZE[0]
    height = len(specs)*SIZE[1]
    atlas = Image.new('RGBA', (width, height))
    layers = {layer: Image.new('RGBA', (width, height)) for layer in ('body', 'working_arm', 'frame')}
    actions = {}
    for row, (action, wrists) in enumerate(specs.items()):
        records = []
        for column, wrist in enumerate(wrists):
            native, body, arm, points, source, source_path, lower_top, head_bottom = working_body(name, wrist)
            canvas = Image.new('RGBA', SIZE);canvas.alpha_composite(native, OFFSET)
            held = Image.new('RGBA', SIZE)
            if action == 'lift' and name == 'liam':
                held.alpha_composite(frame(), (round(wrist[0])+8-5, round(wrist[1])+8-1))
                canvas.alpha_composite(held)
                # Restore the palm in front of the handle, giving a true grip.
                hand = tuple(round(v)+8 for v in wrist)
                ImageDraw.Draw(canvas).point(hand, fill='#f0c594')
            rect = [column*40, row*48, 40, 48]
            atlas.alpha_composite(canvas, rect[:2])
            for layer, im in (('body', body), ('working_arm', arm)):
                padded = Image.new('RGBA', SIZE);padded.alpha_composite(im, OFFSET)
                layers[layer].alpha_composite(padded, rect[:2])
            layers['frame'].alpha_composite(held, rect[:2])
            records.append({'rect': rect, 'duration_ms': 160 if action == 'work' else 180,
                            'joints': points, 'hand': [round(wrist[0])+8, round(wrist[1])+8],
                            'native_wrist': list(wrist)})
        actions[action] = records
    sheet_path = save(f'poses/{name}.png', atlas)
    source_name = save(f'poses/{name}_source.png', source)
    layer_paths = {key: save(f'poses/{name}_{key}.png', value) for key, value in layers.items()}
    return json_file(f'poses/{name}.json', {
        'canvas': list(SIZE), 'draw_anchor': list(ANCHOR), 'source_offset': list(OFFSET),
        'source_canvas': [24, 36], 'source': source_name,
        'source_idle': source_path.relative_to(ROOT).as_posix(),
        'source_sha256': hashlib.sha256(source_path.read_bytes()).hexdigest(),
        'sheet': sheet_path, 'actions': actions, 'layers': layer_paths,
        'arm_lengths': [3.2, 3.2] if name == 'liam' else [4., 4.] if name == 'mira' else [4.5, 4.5],
        'head_pixels_preserved_above_y': head_bottom, 'lower_body_preserved_from_y': lower_top,
        'facing': 'left' if name == 'mira' else 'right',
        'world_work_hand': {'liam': [652, 489], 'mira': [676, 488], 'caelan': [636, 488]}[name],
        **({'world_support_hand': [649, 505], 'work_station': [626, 500],
            'support_station': [640, 514], 'working_arm': 'far'} if name == 'caelan' else {}),
        'frame_handle': [5, 1], 'lift_height_pixels': 2 if name == 'liam' else 0,
    })


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    poses = {name: build_poses(name) for name in ('liam', 'mira', 'caelan')}
    table_path = save('props/table.png', table())
    frame_path = save('props/frame.png', frame())
    states = {state: save(f'props/{state}.png', craft_surface(state))
              for state in ('drawing', 'materials', 'test', 'partial', 'frame', 'lifted', 'ready')}
    school_drawing = save('props/school_drawing.png', drawing_image())
    props = [
        {'id': 'craft_table', 'scene': 'eldenmere.playable', 'position': [636, 478],
         'sort_y': 497, 'states': {'rest': table_path}, 'footprint': [638, 491, 60, 6]},
        {'id': 'craft_surface', 'scene': 'eldenmere.playable', 'position': [636, 454],
         'sort_y': 497, 'states': states},
        {'id': 'school_drawing', 'scene': 'school', 'position': [305, 262],
         'sort_y': 280, 'states': {'drawing': school_drawing}},
    ]
    json_file('art.json', {'poses': poses, 'props': props, 'frame': frame_path,
                           'frame_handle': [5, 1], 'frame_is_lit': False,
                           'design': 'Liam\'s small, vented tower frame; no paper or flame yet.'})
    json_file('layout.json', {
        'invitation': [386, 326], 'tomas_invitation': [420, 348],
        'school': [254, 302], 'classroom': [254, 302],
        'school_approach': [672, 750], 'school_entry': [216, 342],
        'school_teacher': [266, 246], 'school_liam': [318, 246], 'school_tomas': [228, 270],
        'school_children': {'tessa': [66, 222], 'finn': [154, 222], 'rowan': [270, 222],
                            'ada': [358, 222], 'pippa': [154, 314]},
        'workshop': [623, 512], 'workshop_mira': [682, 500],
        'workshop_liam': [646, 500], 'workshop_tomas': [710, 516],
        'assemble_player': [626, 500], 'lift_player': [640, 514],
        'craft_table': [636, 478], 'craft_surface': [636, 454],
        'craft_footprint': [638, 491, 60, 6], 'frame_ready_position': [646, 489],
        'school_exit': [216, 354], 'workshop_route': [[672, 750], [612, 726], [612, 552], [623, 512]],
        'hand_contacts': {'liam': [652, 489], 'mira': [676, 488],
                          'caelan_work': [636, 488], 'caelan_support': [649, 505]},
    })
    print('Built lantern props, registered work/lift poses, and quest stations.')


if __name__ == '__main__':build()
