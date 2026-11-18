"""Register complete authored native Iselin front-walk drawings for review.

Source strips have audited crown/waist landmarks. One whole-drawing density
per strip preserves body proportions; neither feet nor occupied pose heights
determine scale or vertical registration. Campaign bindings are untouched.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import io
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_mira_combat import _main_component

SOURCE = ROOT / 'assets/source/characters/iselin/native_walk_front'
OUTPUT = ROOT / 'assets/characters/iselin/native_walk_front'
REVIEW = ROOT / 'docs/reviews/iselin_native_front_walk'
# Audited horizontal waistband centers and crown rows in each source strip.
# All exports share the approved idle's crown y1 / waistband y18 registration.
STRIPS = ((26, 379), (34, 378), (31, 403), (36, 379))
PHASES = ('right_contact', 'right_settle', 'left_release', 'left_recovery',
          'left_passing', 'left_advance', 'left_reach', 'left_precontact',
          'left_contact', 'left_settle', 'right_release', 'right_recovery',
          'right_passing', 'right_advance', 'right_reach', 'right_precontact')


def png(image):
    stream = io.BytesIO()
    image.save(stream, format='PNG', optimize=True)
    return stream.getvalue()


def json_bytes(value):
    return (json.dumps(value, indent=2) + '\n').encode()


def products():
    outputs = {}
    frames = []
    records = []
    approved_idle_path = ROOT / 'assets/characters/iselin/native_idles/idle_front.png'
    approved_idle = Image.open(approved_idle_path).convert('RGBA')
    # The complete generated poses have inconsistent hair/face proportions at
    # strip joins. Preserve the approved, stationary front-facing head pixels
    # after whole-character authoring, as allowed by the standard's documented
    # regional-preservation workflow. All moving anatomy remains authored below
    # this boundary; no limb is assembled, rotated, stretched or translated.
    protected_head = approved_idle.crop((0, 0, 24, 12))
    for strip_index, (crown, waist) in enumerate(STRIPS):
        source_path = SOURCE / f'batch_{strip_index + 1}.png'
        source = Image.open(source_path).convert('RGBA')
        if source.width % 4:
            raise ValueError('Source must have four equal-width cells')
        width = source.width // 4
        scale = 17 / (waist - crown)
        for col in range(4):
            cell = source.crop((col * width, 0, (col + 1) * width, source.height))
            cell.putalpha(cell.getchannel('A').point(lambda a: 255 if a >= 220 else 0))
            # Extract the connected complete drawing, discarding detached
            # transparent-matte specks without constructing or moving anatomy.
            cell = _main_component(cell)
            bounds = cell.getbbox()
            head_bounds = cell.crop((0, crown, width, crown + 180)).getbbox()
            if bounds is None or head_bounds is None:
                raise ValueError('Missing whole drawing/head in source')
            head_x = (head_bounds[0] + head_bounds[2]) / 2
            # Keep the complete fixed source cell so rounded sample dimensions
            # cannot change the horizontal scale between different silhouettes.
            size = (round(width * scale), round(source.height * scale))
            origin = (round(12 - head_x * scale),
                      round(1 - crown * scale))
            scaled = cell.resize(size, Image.Resampling.NEAREST)
            occupied = scaled.getbbox()
            if (origin[0] + occupied[0] < 0 or origin[1] + occupied[1] < 0
                    or origin[0] + occupied[2] > 24 or origin[1] + occupied[3] > 36):
                raise ValueError(('Clipped source drawing', strip_index, col))
            frame = Image.new('RGBA', (24, 36))
            frame.alpha_composite(scaled, origin)
            frame.paste(protected_head, (0, 0))
            index = len(frames)
            frames.append(frame)
            outputs[OUTPUT / f'frame_{index + 1:02}.png'] = png(frame)
            records.append({'frame': index + 1, 'phase': PHASES[index],
                            'source': source_path.name, 'column': col,
                            'source_cell': [col * width, 0, width, source.height],
                            'opaque_bounds': list(bounds), 'crown_row': crown,
                            'waist_row': waist, 'head_center_x': head_x,
                            'uniform_scale': scale, 'sample_size': list(size),
                            'destination_origin': list(origin),
                            'occupied_bounds': list(frame.getbbox())})
    sheet = Image.new('RGBA', (24 * 16, 36))
    actor_sheet = Image.new('RGBA', (24 * 20, 36))
    idles = {}
    for index, direction in enumerate(('front', 'left', 'right', 'back')):
        idle = Image.open(ROOT / f'assets/characters/iselin/native_idles/idle_{direction}.png').convert('RGBA')
        actor_sheet.alpha_composite(idle, (index * 24, 0))
        idles[direction] = [index * 24, 0, 24, 36]
    for index, frame in enumerate(frames):
        sheet.alpha_composite(frame, (index * 24, 0))
        actor_sheet.alpha_composite(frame, ((index + 4) * 24, 0))
    outputs[OUTPUT / 'spritesheet.png'] = png(sheet)
    outputs[OUTPUT / 'review_spritesheet.png'] = png(actor_sheet)
    frame_records = [{'file': f'frame_{index + 1:02}.png',
                      'rect': [index * 24, 0, 24, 36], 'duration_ms': 35,
                      'phase': PHASES[index]} for index in range(16)]
    outputs[OUTPUT / 'animation.json'] = json_bytes({
        'character': 'iselin', 'animation': 'walk.front',
        'status': 'awaiting user review; campaign not activated',
        'frame_size': [24, 36], 'artwork_pixels_per_world_pixel': 1,
        'draw_anchor': [12, 30], 'foot_anchor': [12, 34],
        'cycle_ms': 560, 'loop': True, 'frames': frame_records,
        'construction': 'Complete authored drawings; source crown/waist registration, no limb rig.',
    })
    outputs[OUTPUT / 'review_actor.json'] = json_bytes({
        'sheet': 'assets/characters/iselin/native_walk_front/review_spritesheet.png',
        'idles': idles,
        'walks': {'front': [{'rect': [(index + 4) * 24, 0, 24, 36], 'duration_ms': 35}
                            for index in range(16)]},
        'status': 'Review-only native actor; other walk directions not authored.',
    })
    board = Image.new('RGB', (768, 728), '#e8edf2')
    draw = ImageDraw.Draw(board)
    font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    font = ImageFont.truetype(font_path, 14) if Path(font_path).exists() else ImageFont.load_default()
    draw.text((12, 10), 'ISELIN / FRONT WALK / 16 x 35 ms / native 24 x 36', font=font, fill='#263c35')
    for index, frame in enumerate(frames):
        x, y = 12 + (index % 4) * 192, 42 + (index // 4) * 170
        draw.text((x, y), f'{index + 1:02} {PHASES[index]}', font=font, fill='#263c35')
        enlarged = frame.resize((96, 144), Image.Resampling.NEAREST)
        board.paste(enlarged, (x + 36, y + 20), enlarged)
    outputs[REVIEW / 'numbered_frames.png'] = png(board)
    outputs[SOURCE / 'registration.json'] = json_bytes({
        'generation_tool': 'image_gen.imagegen',
        'appearance_reference': 'assets/characters/iselin/native_idles/idle_front.png',
        'construction': 'Complete contact keys and four complete-drawing batches; no detached limbs, mirrored costume or anatomy generator.',
        'export': 'Hard alpha220, largest connected drawing, whole-pose nearest sampling; common crown/waist density per strip, no boot-bound normalization.',
        'protected_region': {
            'source': str(approved_idle_path.relative_to(ROOT)),
            'source_sha256': sha256(approved_idle_path.read_bytes()).hexdigest(),
            'rect_xywh': [0, 0, 24, 12],
            'method': 'Restore approved stationary head/face pixels after complete-drawing export; moving body below y12 remains authored.',
            'reason': 'Prevent inconsistent source-strip head width and hair silhouettes from creating a twitch at batch joins.',
        },
        'target_crown_y': 1, 'target_waist_y': 18,
        'source_sha256': {p.name: sha256(p.read_bytes()).hexdigest()
                          for p in sorted(SOURCE.glob('*.png'))},
        'records': records,
        'exports': {str(path.relative_to(ROOT)): sha256(data).hexdigest()
                    for path, data in outputs.items()},
        'status': 'awaiting user review',
    })
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = products()
    if args.check:
        stale = [str(path.relative_to(ROOT)) for path, data in outputs.items()
                 if not path.exists() or path.read_bytes() != data]
        if stale:
            raise SystemExit('Stale front walk exports: ' + ', '.join(stale))
        print('Native front walk exports match authored sources.')
        return
    for path, data in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    print('Exported sixteen complete native front-walk drawings and review-only actor.')


if __name__ == '__main__':
    main()
