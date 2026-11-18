"""Export complete native Iselin left-walk drawings for in-game review.

One source density and source-cell grid serve the full two-step cycle. Feet,
individual pose bounds and limb transforms never determine registration.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_mira_combat import _main_component
from tools.export_iselin_native_front_walk import png, json_bytes

SOURCE = ROOT / 'assets/source/characters/iselin/native_walk_left'
OUTPUT = ROOT / 'assets/characters/iselin/native_walk_left'
REVIEW = ROOT / 'docs/reviews/iselin_native_left_walk'
PHASES = ('near_contact', 'near_settle', 'far_release', 'far_recovery',
          'far_passing', 'far_advance', 'far_reach', 'far_precontact',
          'far_contact', 'far_settle', 'near_release', 'near_recovery',
          'near_passing', 'near_advance', 'near_reach', 'near_precontact')


def products():
    path = SOURCE / 'authored.png'
    source = Image.open(path).convert('RGBA')
    if source.size != (1086, 1448):
        raise ValueError('Unexpected complete-drawing source grid')
    idle_path = ROOT / 'assets/characters/iselin/native_idles/idle_left.png'
    idle = Image.open(idle_path).convert('RGBA')
    # Preserve the approved profile/face after complete-figure authoring, as in
    # the approved front walk. A single-pixel walking settle keeps contact feet
    # on the declared ground line without scaling individual poses by boots.
    head = idle.crop((0, 0, 24, 12))
    outputs = {}
    frames = []
    records = []
    for index in range(16):
        row, col = divmod(index, 4)
        rect = (round(col * source.width / 4), row * 362,
                round((col + 1) * source.width / 4), (row + 1) * 362)
        cell = source.crop(rect)
        cell.putalpha(cell.getchannel('A').point(lambda a: 255 if a >= 220 else 0))
        cell = _main_component(cell)
        bounds = cell.getbbox()
        # Half-pixel source column boundaries round to271/272px. Pad their
        # transparent right edge so every pose has exactly the same density.
        registered = Image.new('RGBA', (272, 362))
        registered.alpha_composite(cell, (0, 0))
        scaled = registered.resize((27, 36), Image.Resampling.NEAREST)
        occupied = scaled.getbbox()
        origin = (-2, -1)
        if (occupied is None or occupied[0] + origin[0] < 0
                or occupied[1] + origin[1] < 0
                or occupied[2] + origin[0] > 24
                or occupied[3] + origin[1] > 36):
            raise ValueError(('Clipped complete left-walk drawing', index + 1))
        frame = Image.new('RGBA', (24, 36))
        frame.alpha_composite(scaled, origin)
        frame.paste((0, 0, 0, 0), (0, 0, 24, 13))
        frame.paste(head, (0, 1))
        frames.append(frame)
        outputs[OUTPUT / f'frame_{index + 1:02}.png'] = png(frame)
        records.append({'frame': index + 1, 'phase': PHASES[index],
                        'source_rect': list(rect), 'opaque_source_bounds': list(bounds),
                        'source_cell_size': [272, 362], 'nominal_density_scale': .1,
                        'rounded_sample_size': [27, 36], 'destination_origin': list(origin),
                        'occupied_bounds': list(frame.getbbox())})
    sheet = Image.new('RGBA', (24 * 16, 36))
    actor_sheet = Image.new('RGBA', (24 * 20, 36))
    idles = {}
    for index, direction in enumerate(('front', 'left', 'right', 'back')):
        image = Image.open(ROOT / f'assets/characters/iselin/native_idles/idle_{direction}.png').convert('RGBA')
        actor_sheet.alpha_composite(image, (index * 24, 0))
        idles[direction] = [index * 24, 0, 24, 36]
    for index, frame in enumerate(frames):
        sheet.alpha_composite(frame, (index * 24, 0))
        actor_sheet.alpha_composite(frame, ((index + 4) * 24, 0))
    outputs[OUTPUT / 'spritesheet.png'] = png(sheet)
    outputs[OUTPUT / 'review_spritesheet.png'] = png(actor_sheet)
    outputs[OUTPUT / 'animation.json'] = json_bytes({
        'character': 'iselin', 'animation': 'walk.left',
        'status': 'user-approved left walk; integrated via canonical Iselin actor',
        'frame_size': [24, 36], 'artwork_pixels_per_world_pixel': 1,
        'draw_anchor': [12, 30], 'foot_anchor': [12, 34],
        'cycle_ms': 560, 'loop': True,
        'frames': [{'file': f'frame_{index + 1:02}.png', 'rect': [index * 24, 0, 24, 36],
                    'duration_ms': 35, 'phase': PHASES[index]} for index in range(16)],
        'construction': 'Complete left-specific drawings; no limb rig or mirrored costume.',
    })
    outputs[OUTPUT / 'review_actor.json'] = json_bytes({
        'sheet': 'assets/characters/iselin/native_walk_left/review_spritesheet.png',
        'idles': idles,
        'walks': {'left': [{'rect': [(index + 4) * 24, 0, 24, 36], 'duration_ms': 35}
                           for index in range(16)]},
        'status': 'User-approved left walk; isolated inspection actor; canonical gameplay actor is separate.',
    })
    board = Image.new('RGB', (768, 728), '#e8edf2')
    draw = ImageDraw.Draw(board)
    font_path = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    font = ImageFont.truetype(str(font_path), 14) if font_path.exists() else ImageFont.load_default()
    draw.text((12, 10), 'ISELIN / LEFT WALK / 16 x 35 ms / native 24 x 36', font=font, fill='#263c35')
    for index, frame in enumerate(frames):
        x, y = 12 + (index % 4) * 192, 42 + (index // 4) * 170
        draw.text((x, y), f'{index + 1:02} {PHASES[index]}', font=font, fill='#263c35')
        enlarged = frame.resize((96, 144), Image.Resampling.NEAREST)
        board.paste(enlarged, (x + 36, y + 20), enlarged)
    outputs[REVIEW / 'numbered_frames.png'] = png(board)
    outputs[SOURCE / 'registration.json'] = json_bytes({
        'generation_tool': 'image_gen.imagegen',
        'appearance_reference': str(idle_path.relative_to(ROOT)),
        'appearance_reference_sha256': sha256(idle_path.read_bytes()).hexdigest(),
        'construction': 'Complete left-specific key poses and16 complete authored poses; no detached limb assembly or mirrored finished art.',
        'anatomy': 'Near anatomical left, far anatomical right; braid on near shoulder, mantle on far shoulder.',
        'registration': 'One fixed272x362 source grid sampled at nominal0.1 density to27x36; origin[-2,-1] for all16; no per-pose boot normalization.',
        'protected_region': {'source_rect_xywh': [0, 0, 24, 12], 'destination': [0, 1],
                             'reason': 'Preserve approved stationary profile and face through the complete drawn cycle; one-pixel walking settle.',
                             'moving_body': 'Authored braid tail/torso/arms/coat/legs below y13 unchanged.'},
        'source_sha256': {p.name: sha256(p.read_bytes()).hexdigest()
                          for p in sorted(SOURCE.glob('*.png'))},
        'records': records,
        'exports': {str(p.relative_to(ROOT)): sha256(data).hexdigest() for p, data in outputs.items()},
        'status': 'user-approved left walk; native actor integrated',
    })
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = products()
    if args.check:
        stale = [str(p.relative_to(ROOT)) for p, data in outputs.items()
                 if not p.exists() or p.read_bytes() != data]
        if stale:
            raise SystemExit('Stale native left-walk exports: ' + ', '.join(stale))
        print('Native left-walk exports match complete authored source.')
        return
    for p, data in outputs.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    print('Exported sixteen complete native left-walk frames and review actor.')


if __name__ == '__main__':
    main()
