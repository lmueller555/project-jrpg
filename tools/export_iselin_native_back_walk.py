"""Export complete native rear-walk drawings with fixed body registration.

Each pose uses the same1/8 source density and192x288 source window. Windows
are placed from head landmarks; feet never determine pose scale or alignment.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_mira_combat import _main_component
from tools.export_iselin_native_front_walk import png, json_bytes

SOURCE = ROOT / 'assets/source/characters/iselin/native_walk_back'
OUTPUT = ROOT / 'assets/characters/iselin/native_walk_back'
REVIEW = ROOT / 'docs/reviews/iselin_native_back_walk'
DIRECTIONS = ('front', 'left', 'right', 'back')
PHASES = ('right_contact', 'right_settle', 'left_release', 'left_recovery',
          'left_passing', 'left_advance', 'left_reach', 'left_precontact',
          'left_contact', 'left_settle', 'right_release', 'right_recovery',
          'right_passing', 'right_advance', 'right_reach', 'right_precontact')


def products():
    source_path = SOURCE / 'authored.png'
    source = Image.open(source_path).convert('RGBA')
    if source.size != (1263, 1245):
        raise ValueError('Unexpected authored rear-walk grid')
    idle_path = ROOT / 'assets/characters/iselin/native_idles/idle_back.png'
    idle = Image.open(idle_path).convert('RGBA')
    head = idle.crop((0, 0, 24, 12))
    outputs, frames, records = {}, [], []
    for index in range(16):
        row, col = divmod(index, 4)
        source_rect = (round(col * source.width / 4), round(row * source.height / 4),
                       round((col + 1) * source.width / 4), round((row + 1) * source.height / 4))
        cell = source.crop(source_rect)
        cell.putalpha(cell.getchannel('A').point(lambda a: 255 if a >= 220 else 0))
        cell = _main_component(cell)
        bounds = cell.getbbox()
        head_bounds = cell.crop((0, 0, cell.width, 100)).getbbox()
        if bounds is None or head_bounds is None:
            raise ValueError('Missing complete rear drawing/head')
        crown = head_bounds[1]
        head_center = (head_bounds[0] + head_bounds[2]) / 2
        # The master has uneven horizontal margins. Translate complete drawing
        # windows to the shared head grid without changing density or anatomy.
        x, y = round(head_center - 96), crown - 8
        window = (x, y, x + 192, y + 288)
        if not (window[0] <= bounds[0] and window[1] <= bounds[1]
                and window[2] >= bounds[2] and window[3] >= bounds[3]):
            raise ValueError(('Clipped complete rear pose', index + 1))
        sampled = cell.crop(window).resize((24, 36), Image.Resampling.NEAREST)
        frame = Image.new('RGBA', (24, 36))
        frame.alpha_composite(sampled, (0, 0))
        # Preserve approved stationary hair/profile pixels after complete-figure
        # authoring. Braid tail, mantle, torso and moving anatomy stay authored.
        frame.paste(head, (0, 0))
        frames.append(frame)
        outputs[OUTPUT / f'frame_{index + 1:02}.png'] = png(frame)
        records.append({'frame': index + 1, 'phase': PHASES[index],
                        'source_rect': list(source_rect), 'opaque_bounds': list(bounds),
                        'head_bounds': list(head_bounds), 'crown_row': crown,
                        'head_center_x': head_center, 'registered_source_window': list(window),
                        'source_density_scale': .125, 'frame_size': [24, 36],
                        'occupied_bounds': list(frame.getbbox())})
    sheet = Image.new('RGBA', (384, 36))
    actor_sheet = Image.new('RGBA', (480, 36))
    idles = {}
    for index, direction in enumerate(DIRECTIONS):
        image = Image.open(ROOT / f'assets/characters/iselin/native_idles/idle_{direction}.png').convert('RGBA')
        actor_sheet.alpha_composite(image, (index * 24, 0))
        idles[direction] = [index * 24, 0, 24, 36]
    for index, frame in enumerate(frames):
        sheet.alpha_composite(frame, (index * 24, 0))
        actor_sheet.alpha_composite(frame, ((index + 4) * 24, 0))
    outputs[OUTPUT / 'spritesheet.png'] = png(sheet)
    outputs[OUTPUT / 'review_spritesheet.png'] = png(actor_sheet)
    outputs[OUTPUT / 'animation.json'] = json_bytes({
        'character': 'iselin', 'animation': 'walk.back',
        'status': 'awaiting user review; campaign not activated',
        'frame_size': [24, 36], 'artwork_pixels_per_world_pixel': 1,
        'draw_anchor': [12, 30], 'foot_anchor': [12, 34], 'cycle_ms': 560, 'loop': True,
        'frames': [{'file': f'frame_{i + 1:02}.png', 'rect': [i * 24, 0, 24, 36],
                    'duration_ms': 35, 'phase': PHASES[i]} for i in range(16)],
        'construction': 'Complete rear-specific drawings with head/body registration; no limb rig.',
    })
    outputs[OUTPUT / 'review_actor.json'] = json_bytes({
        'sheet': 'assets/characters/iselin/native_walk_back/review_spritesheet.png',
        'idles': idles,
        'walks': {'back': [{'rect': [(i + 4) * 24, 0, 24, 36], 'duration_ms': 35}
                           for i in range(16)]},
        'status': 'Review-only native back walk; campaign bindings unchanged.',
    })
    board = Image.new('RGB', (768, 728), '#e8edf2')
    draw = ImageDraw.Draw(board)
    font_path = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    font = ImageFont.truetype(str(font_path), 14) if font_path.exists() else ImageFont.load_default()
    draw.text((12, 10), 'ISELIN / BACK WALK / 16 x 35 ms / native 24 x 36', font=font, fill='#263c35')
    for i, frame in enumerate(frames):
        x, y = 12 + (i % 4) * 192, 42 + (i // 4) * 170
        draw.text((x, y), f'{i + 1:02} {PHASES[i]}', font=font, fill='#263c35')
        enlarged = frame.resize((96, 144), Image.Resampling.NEAREST)
        board.paste(enlarged, (x + 36, y + 20), enlarged)
    outputs[REVIEW / 'numbered_frames.png'] = png(board)
    outputs[SOURCE / 'registration.json'] = json_bytes({
        'generation_tool': 'image_gen.imagegen',
        'appearance_reference': str(idle_path.relative_to(ROOT)),
        'appearance_reference_sha256': sha256(idle_path.read_bytes()).hexdigest(),
        'construction': 'Complete rear key studies and16 complete authored drawings; no limb assembly, mirrored front art or boot-bound normalization.',
        'anatomy': 'Rear anatomical left=image left braid root; anatomical right=image right mantle. Forward/away limbs foreshorten upward; trailing limbs toward camera extend lower.',
        'registration': 'Every whole drawing uses a192x288 source window at1/8 density, placed by head crown/center; no per-pose rescaling or foot registration.',
        'protected_region': {'source_rect_xywh': [0, 0, 24, 12], 'destination': [0, 0],
                             'reason': 'Preserve the approved stationary rear hair/head silhouette after complete-frame export.',
                             'moving_body': 'Authored braid bend/mantle/torso/arms/coat/legs below y12 remain intact.'},
        'source_sha256': {p.name: sha256(p.read_bytes()).hexdigest()
                          for p in sorted(SOURCE.glob('*.png'))},
        'records': records,
        'exports': {str(p.relative_to(ROOT)): sha256(data).hexdigest() for p, data in outputs.items()},
        'status': 'awaiting user review',
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
            raise SystemExit('Stale native back-walk exports: ' + ', '.join(stale))
        print('Native back-walk exports match complete authored source.')
        return
    for p, data in outputs.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    print('Exported sixteen complete native back-walk frames and review actor.')


if __name__ == '__main__':
    main()
