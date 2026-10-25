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
)


def blank(size=SIZE):
    return Image.new('RGBA', size)


def load(path):
    return Image.open(ROOT/path).convert('RGBA')


def pixel_colors(image):
    return {tuple(pixel) for pixel in image.get_flattened_data() if pixel[3]}


def seated(character, phase=0):
    """Keep approved head/torso pixels; fold the lower legs at the chair seat.

    The two short forearm segments keep their lengths as the elbow pivots. A
    two-pixel wrist reach supplies the plate push; the body does not stretch.
    """
    right = character == 'caelan'
    source = load(SOURCE_PATHS[0] if right else SOURCE_PATHS[2])
    result = blank()
    result.alpha_composite(source.crop((0, 0, 24, 25)), (0, 3))
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
               'caelan_sleep_head.png': sleep_head(), 'plate.png': plate()}
    exports.update({f'tomas_plate_push/frame_{i+1:02}.png': seated('tomas', i)
                    for i in range(4)})
    for path, image in exports.items():
        destination = OUT/path
        destination.parent.mkdir(parents=True, exist_ok=True)
        image.save(destination)
        assert set(image.getchannel('A').tobytes()) <= {0, 255}
        source = (load(SOURCE_PATHS[0]) if path.startswith('caelan_seated') else
                  load(SOURCE_PATHS[1]) if path.startswith('caelan_sleep') else
                  load(SOURCE_PATHS[3]) if path == 'plate.png' else load(SOURCE_PATHS[2]))
        assert pixel_colors(image) <= pixel_colors(source), path
    assert len({exports[f'tomas_plate_push/frame_{i:02}.png'].tobytes() for i in range(1, 5)}) == 4
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
        'notes': 'Approved design pixels and palettes retained. No original PNG is changed. The scene owns the temporary seating and table depth.'
    }
    (OUT/'recipe.json').write_text(json.dumps(recipe, indent=2)+'\n', encoding='utf-8')
    (OUT/'README.md').write_text('''# Sanctuary opening poses

Native transparent 24×36 breakfast bodies reuse the approved Caelan/Tomas
profiles. Heads and shoulders drop together by three pixels; compact bent knees
and boots retain the shared foot baseline. Tomas faces left; Caelan faces right.
The four plate-push frames pivot two short arm segments, reaching only two pixels.
The separate 8×4 plate moves by two pixels in contact with his wrist.

The head-only sleeping sprite keeps Caelan's approved hair/face and closes both
eyes. Place its image at `[48,123]` over the existing bedroom bed `[36,108]`;
the original quilt covers the body. The scene must suppress the standing body
while this overlay is shown, then restore Caelan at the clear bedside.

All body frames use draw anchor `[12,30]`. Suggested table positions and hand
landmarks are in `recipe.json`. The scene owns temporary furniture registration
and foot collision during the locked breakfast scene. The exports never change
the ordinary standing/walking artwork or approved furniture images.

Rebuild with `python tools/build_sanctuary_opening_poses.py` (Pillow required).
The builder checks hard alpha, source palettes, distinct motion poses and the
source PNG hashes. Runtime uses only the checked-in PNGs.
''', encoding='utf-8')
    assert hashes == {path: hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in SOURCE_PATHS}
    print('Built eight opening pose exports; approved source PNGs unchanged.')


if __name__ == '__main__':
    build()
