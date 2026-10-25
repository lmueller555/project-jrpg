"""Register approved character pixels onto compact breakfast and pillow poses."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'assets/story/sanctuary_opening/poses'
SIZE = (24, 36)
SOURCE_PATHS = (
    'assets/characters/caelan/idle_right.png',
    'assets/characters/caelan/idle_front.png',
    'assets/characters/tomas/idle_left.png',
    'assets/terrain/eldenmere/sanctuary_interior/props/breakfast.png',
    'assets/terrain/eldenmere/cottage_furniture/sprites/bed.png',
    'assets/characters/tomas/idle_front.png',
)


def blank(size=SIZE):
    return Image.new('RGBA', size)


def load(path):
    return Image.open(ROOT/path).convert('RGBA')


def pixel_colors(image):
    return {tuple(pixel) for pixel in image.get_flattened_data() if pixel[3]}


def seated(character, phase=0, arm=None, upper_bob=0):
    """Keep approved head/torso pixels; fold the lower legs at the chair seat.

    The two short forearm segments keep their lengths as the elbow pivots. A
    two-pixel wrist reach supplies the plate push; the body does not stretch.
    """
    right = character == 'caelan'
    source = load(SOURCE_PATHS[0] if right else SOURCE_PATHS[2])
    result = blank()
    result.alpha_composite(source.crop((0, 0, 24, 25)), (0, 3+upper_bob))
    draw = ImageDraw.Draw(result)
    outline = '#1a0e16'
    pants = '#645450' if right else '#51413b'
    trouser_shadow = '#573422' if right else '#352a29'
    boot = '#8b5531' if right else '#84512e'
    boot_light = '#b67644' if right else '#9d6238'
    sleeve = '#fbeed0'
    skin = '#e8c49d'
    skin_shadow = '#e99f55' if right else '#eda052'

    def point(x, y):
        return (x, y) if right else (23-x, y)

    # A compact lap, two bent knees, and the same feet baseline as the idles.
    draw.polygon([point(10, 27), point(14, 27), point(18, 29),
                  point(18, 32), point(14, 32), point(14, 30), point(10, 30)], fill=outline)
    draw.polygon([point(11, 28), point(14, 28), point(17, 29),
                  point(17, 31), point(15, 31), point(15, 29), point(11, 29)], fill=pants)
    draw.line([point(11, 30), point(14, 30), point(14, 33)], fill=trouser_shadow, width=2)
    draw.line([point(17, 30), point(17, 33)], fill=pants, width=2)
    for x, end in ((13, 16), (16, 20)):
        draw.line([point(x, 33), point(end, 33)], fill=outline, width=3)
        draw.line([point(x, 33), point(end, 33)], fill=boot, width=1)
        draw.point(point(end-1, 32), fill=boot_light)

    if right:
        # Replace the idle's hanging near forearm with a bent resting sleeve.
        draw.rectangle((7, 23, 11, 27), fill=(0, 0, 0, 0))
        shoulder, elbow, wrist = (9, 21), (10, 25), (16, 25)
    else:
        draw.rectangle((14, 23, 18, 27), fill=(0, 0, 0, 0))
        shoulder = (14, 21)
        elbow, wrist = (((13, 25), (7, 25)), ((12, 25), (6, 25)),
                        ((11, 24), (5, 25)), ((13, 25), (7, 26)))[phase]
    if arm is not None:
        shoulder, elbow, wrist = arm
    if upper_bob:
        shoulder, elbow, wrist = [(x, y+upper_bob) for x, y in (shoulder, elbow, wrist)]
    draw.line([shoulder, elbow, wrist], fill=outline, width=3)
    draw.line([shoulder, elbow, wrist], fill=sleeve, width=2)
    draw.point(wrist, fill=skin)
    draw.point((wrist[0], wrist[1]+1), fill=skin_shadow)
    return result


def sleep_head():
    source = load(SOURCE_PATHS[1])
    result = blank()
    result.alpha_composite(source.crop((0, 0, 24, 13)), (0, 0))
    draw = ImageDraw.Draw(result)
    # Remove the approved front eyes' two-pixel vertical opening, then draw
    # short horizontal eyelids in an existing warm hair shadow.
    for x in (10, 13):
        draw.line((x, 9, x, 10), fill='#e8c49d')
    draw.line((9, 10, 10, 10), fill='#573422')
    draw.line((13, 10, 14, 10), fill='#573422')
    return result


def awake_head():
    result = blank()
    result.alpha_composite(load(SOURCE_PATHS[1]).crop((0, 0, 24, 13)))
    return result


def awake_body():
    """An awake head with one arm folded under the covering quilt."""
    result = load(SOURCE_PATHS[1])
    draw = ImageDraw.Draw(result)
    arm = [(7, 17), (8, 21), (13, 20)]
    draw.line(arm, fill='#1a0e16', width=3)
    draw.line(arm, fill='#fbeed0', width=2)
    draw.point(arm[-1], fill='#e8c49d')
    return result


def bed_edge():
    """Front-facing torso on the bed edge, with two compact folded knees."""
    result = blank()
    source = load(SOURCE_PATHS[1])
    result.alpha_composite(source.crop((0, 0, 24, 25)), (0, 2))
    draw = ImageDraw.Draw(result)
    draw.polygon([(7, 26), (16, 26), (18, 29), (17, 32),
                  (14, 33), (10, 33), (7, 31)], fill='#1a0e16')
    draw.polygon([(8, 27), (15, 27), (17, 29), (15, 30),
                  (13, 29), (10, 30), (8, 29)], fill='#645450')
    draw.line((10, 29, 10, 33), fill='#573422', width=2)
    draw.line((15, 29, 15, 33), fill='#645450', width=2)
    for x in (9, 14):
        draw.line((x, 33, x+3, 33), fill='#1a0e16', width=3)
        draw.line((x, 33, x+3, 33), fill='#8b5531')
        draw.point((x+2, 32), fill='#b67644')
    return result


def sit_pose(character, phase):
    if phase == 3:
        return seated(character)
    source = load(SOURCE_PATHS[0] if character == 'caelan' else SOURCE_PATHS[2])
    if phase == 0:
        return source
    if phase == 1:
        # The shoulders and head lower as one unit. Original straight legs
        # still support the body while it begins to bend toward the seat.
        result = blank()
        result.alpha_composite(source.crop((0, 0, 24, 25)), (0, 1))
        result.alpha_composite(source.crop((0, 25, 24, 36)), (0, 25))
        return result
    result = seated(character)
    # The penultimate bend is one pixel higher than the final settled body;
    # retain its folded legs and foot baseline rather than scaling a sprite.
    result.paste((0, 0, 0, 0), (0, 0, 24, 27))
    result.alpha_composite(source.crop((0, 0, 24, 25)), (0, 2))
    return result


EATING_ARMS = {
    'caelan': [((9, 21), (10, 25), (16, 25)),
               ((9, 21), (12, 24), (18, 25)),
               ((9, 21), (11, 21), (14, 16)),
               ((9, 21), (10, 23), (14, 19))],
    'tomas': [((14, 21), (13, 25), (7, 25)),
              ((14, 21), (11, 24), (5, 25)),
              ((14, 21), (12, 22), (9, 18)),
              ((14, 21), (13, 24), (9, 21))],
}
CUP_ARMS = [((9, 21), (10, 25), (16, 25)),
            ((9, 21), (12, 23), (16, 20)),
            ((9, 21), (13, 23), (20, 23)),
            ((9, 21), (10, 25), (16, 25))]


def eating(character, phase):
    result = seated(character, arm=EATING_ARMS[character][phase],
                    upper_bob=1 if phase == 2 else 0)
    if phase in (1, 2):
        x, y = EATING_ARMS[character][phase][-1]
        y += 1 if phase == 2 else 0
        draw = ImageDraw.Draw(result)
        # A tiny piece of bread reaches the closed mouth; expression stays
        # subtle and no open black mouth is added to the approved face.
        draw.point((x, y-1), fill='#b67644' if character == 'caelan' else '#9d6238')
    return result


def seated_cup(phase):
    result = seated('caelan', arm=CUP_ARMS[phase])
    if phase == 3:
        # Finishing with the head turned toward Serene makes the fourth pose
        # distinct without a prolonged reach or a second cup appearing.
        result = seated_glance('caelan', result)
    return result


def seated_glance(character, body=None):
    result = seated(character) if body is None else body.copy()
    front = load(SOURCE_PATHS[1] if character == 'caelan' else SOURCE_PATHS[5])
    height = 13 if character == 'caelan' else 17
    result.paste((0, 0, 0, 0), (0, 0, 24, height+3))
    result.alpha_composite(front.crop((0, 0, 24, height)), (0, 3))
    return result


def cup():
    result = blank((6, 6))
    draw = ImageDraw.Draw(result)
    draw.rectangle((1, 1, 4, 4), fill='#b18e68')
    draw.line((1, 1, 4, 1), fill='#e1d6bc')
    draw.line((2, 4, 4, 4), fill='#737e7a')
    draw.line((4, 1, 5, 1), fill='#737e7a')
    draw.line((5, 1, 5, 3), fill='#737e7a')
    draw.point((4, 3), fill='#737e7a')
    draw.line((2, 2, 3, 2), fill='#d3c6a4')
    return result


def plate():
    result = blank((8, 4))
    draw = ImageDraw.Draw(result)
    draw.ellipse((0, 0, 7, 3), fill='#737e7a')
    draw.ellipse((1, 0, 6, 2), fill='#e1d6bc')
    draw.line((2, 1, 5, 1), fill='#d3c6a4')
    draw.rectangle((3, 1, 4, 1), fill='#b18e68')
    return result


def build():
    hashes = {path: hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
              for path in SOURCE_PATHS}
    exports = {'caelan_seated.png': seated('caelan'),
               'tomas_seated.png': seated('tomas'),
               'caelan_sleep_head.png': sleep_head(), 'plate.png': plate(),
               'cup.png': cup(),
               'caelan_seated_glance.png': seated_glance('caelan'),
               'tomas_seated_glance.png': seated_glance('tomas')}
    exports.update({f'tomas_plate_push/frame_{i+1:02}.png': seated('tomas', i)
                    for i in range(4)})
    actions = {}

    def action(name, images, durations, positions=None, kinds=None, wrists=None):
        records = []
        for i, image in enumerate(images):
            file = f'frame_{i+1:02}.png'
            exports[f'{name}/{file}'] = image
            record = {'file': file, 'duration_ms': durations[i],
                      'kind': kinds[i] if kinds else 'body', 'draw_anchor': [12, 30]}
            if positions is not None:
                record['display_position'] = positions[i]
            if wrists is not None:
                record['wrist'] = list(wrists[i])
            records.append(record)
        actions[name] = {'id': name, 'frame_size': [24, 36], 'draw_anchor': [12, 30],
                         'frame_count': 4, 'duration_ms': sum(durations), 'loop': False,
                         'frames': records,
                         'registration': 'Interpolate display positions continuously; logical standing feet stay on clear floor.'}

    action('wake_up', [sleep_head(), awake_body(), bed_edge(), load(SOURCE_PATHS[1])],
           [140, 280, 260, 180],
           [[60, 153], [60, 153], [90, 170], [90, 186]],
           ['pillow_head', 'body', 'body', 'body'])
    for index, bottom in enumerate((13, 13, 15, 13)):
        actions['wake_up']['frames'][index]['head_bottom'] = bottom
    for index in (1, 2):
        actions['wake_up']['frames'][index]['bed_occlusion_below_head'] = True
        actions['wake_up']['frames'][index]['bed_occlusion'] = True
    actions['wake_up']['bed_rect'] = [36, 108, 48, 72]
    actions['wake_up']['standing_position'] = [90, 186]
    actions['wake_up']['registration'] = ('Keep the pillow-head key anchored. From the awake full-body key, '
                                          'interpolate the whole body toward the right bed edge. Restore '
                                          'blanket pixels only below the current head_bottom and inside bed_rect.')
    for who, start, end in (('caelan', [108, 200], [138, 200]),
                            ('tomas', [228, 200], [198, 200])):
        images = [sit_pose(who, phase) for phase in range(4)]
        positions = [[round(start[0]+(end[0]-start[0])*p), 200]
                     for p in (0, .55, .85, 1)]
        action(f'{who}_sit', images, [180, 160, 160, 200], positions)
        action(f'{who}_stand', list(reversed(images)), [160, 150, 170, 180],
               list(reversed(positions)))
        action(f'{who}_eat', [eating(who, phase) for phase in range(4)],
               [160, 180, 240, 180],
               wrists=[arm[-1] for arm in EATING_ARMS[who]])
    action('caelan_seated_cup', [seated_cup(phase) for phase in range(4)],
           [140, 200, 240, 180], wrists=[arm[-1] for arm in CUP_ARMS])
    actions['caelan_seated_cup']['cup_attachment_offset'] = [-2, -4]
    actions['caelan_seated_cup']['table_cup_position'] = [146, 189]
    actions['caelan_seated_cup']['release_frame'] = 3
    for path, image in exports.items():
        destination = OUT/path
        destination.parent.mkdir(parents=True, exist_ok=True)
        image.save(destination)
        assert set(image.getchannel('A').tobytes()) <= {0, 255}
        if path in ('plate.png', 'cup.png'):
            allowed = pixel_colors(load(SOURCE_PATHS[3]))
        elif path.startswith('tomas'):
            allowed = pixel_colors(load(SOURCE_PATHS[2])) | pixel_colors(load(SOURCE_PATHS[5]))
        else:
            allowed = pixel_colors(load(SOURCE_PATHS[0])) | pixel_colors(load(SOURCE_PATHS[1]))
        assert pixel_colors(image) <= allowed, path
    assert len({exports[f'tomas_plate_push/frame_{i:02}.png'].tobytes() for i in range(1, 5)}) == 4
    for name, metadata in actions.items():
        assert len({exports[f'{name}/frame_{i:02}.png'].tobytes() for i in range(1, 5)}) == 4, name
        (OUT/name/'animation.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
    recipe = {
        'id': 'sanctuary_opening_poses', 'status': 'implemented',
        'builder': 'tools/build_sanctuary_opening_poses.py',
        'source_png_sha256': hashes,
        'frame_size': [24, 36], 'draw_anchor': [12, 30], 'foot_baseline': 34,
        'seated': {'caelan': {'file': 'caelan_seated.png', 'facing': 'right', 'wrist': [16, 25]},
                   'tomas': {'file': 'tomas_seated.png', 'facing': 'left', 'wrist': [7, 25]},
                   'head_and_shoulders_drop_px': 3,
                   'suggested_positions': {'caelan': [138, 200], 'tomas': [198, 200]}},
        'sleep': {'file': 'caelan_sleep_head.png', 'occupied_bbox_xyxy': list(exports['caelan_sleep_head.png'].getbbox()),
                  'occupied_rect': [6, 1, 12, 12],
                  'suggested_image_position': [48, 123], 'bed_position': [36, 108],
                  'eyes': 'closed; body is covered by the existing quilt'},
        'plate_push': {'frames': [f'tomas_plate_push/frame_{i:02}.png' for i in range(1, 5)],
                       'frame_duration_ms': 180, 'wrists': [[7, 25], [6, 25], [5, 25], [7, 26]],
                       'elbows': [[13, 25], [12, 25], [11, 24], [13, 25]],
                       'arm_segment_lengths_px': {'upper': '4-5', 'forearm': '6-7'},
                       'plate_offsets_px': [[0, 0], [-1, 0], [-2, 0], [-2, 0]]},
        'plate': {'file': 'plate.png', 'frame_size': [8, 4], 'suggested_position': [185, 191]},
        'cup': {'file': 'cup.png', 'frame_size': [6, 6], 'table_position': [146, 189]},
        'actions': {name: f'{name}/animation.json' for name in actions},
        'fixed_furniture': {'west_chair': [120, 174], 'east_chair': [192, 174], 'table': [144, 168]},
        'standing_positions': {'caelan': [108, 200], 'tomas': [228, 200]},
        'notes': 'Approved design pixels and palettes retained. No original PNG is changed. Furniture registration stays fixed throughout the polished scene.'
    }
    (OUT/'recipe.json').write_text(json.dumps(recipe, indent=2)+'\n', encoding='utf-8')
    (OUT/'README.md').write_text('''# Sanctuary opening poses

Native transparent 24×36 poses reuse the approved Caelan/Tomas profiles and
front views. Each new action has four distinct key poses with variable holds.
Heads and shoulders lower together as the knees bend; boots retain the shared
baseline. Eating uses short elbow pivots, a small bite and a closed-mouth rest.
The cup gesture finishes with a glance toward Serene, without stretching arms.

Actions: `wake_up`, `caelan_sit`, `caelan_stand`, `tomas_sit`, `tomas_stand`,
`caelan_eat`, `tomas_eat`, and `caelan_seated_cup`. Their `animation.json` files
record duration, presentation kind, registration positions and wrist landmarks.
Display positions should interpolate continuously between authored keys. The
waking head begins at image `[48,123]`; its first key stays on the pillow. The
second key supplies a full body beneath the quilt, so the head never travels
alone. The body emerges at the right bed edge and finishes at the clear standing
point `[90,186]`. Head-bottom landmarks guide a dynamic blanket mask below the
chin, clipped to the bed rectangle; the face remains visible at every key.

Dining chairs stay fixed at `[120,174]` and `[192,174]`, around table `[144,168]`.
Standing points are `[108,200]` and `[228,200]`; seated display anchors are
`[138,200]` and `[198,200]`. Body draw anchors remain `[12,30]`. The original
single-pose and plate-nudge paths remain available for older scene code.

The separate 8×4 plate and 6×6 cup use approved breakfast-object colors. Cup
attachment, release frame and final table coordinates are recorded in the action
metadata. No original character or furniture PNG is changed.

Rebuild with `python tools/build_sanctuary_opening_poses.py` (Pillow required).
The builder checks hard alpha, palettes, distinct key poses and source PNG hashes.
Runtime uses only the checked-in exports; no Pillow dependency is introduced.
''', encoding='utf-8')
    assert hashes == {path: hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in SOURCE_PATHS}
    print(f'Built {len(exports)} opening pose exports and {len(actions)} actions; approved source PNGs unchanged.')


if __name__ == '__main__':
    build()
