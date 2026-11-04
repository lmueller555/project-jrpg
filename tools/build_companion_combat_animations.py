"""Export reviewed companion pose atlases through one shared pixel pipeline.

This performs mechanical extraction, binary-alpha conversion, fixed-scale
sampling and ground registration. The source atlases author all anatomy and
equipment. It never paints, stretches or synthesizes character poses.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from statistics import median
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_machinist_assets import authored_cells


SOURCE = ROOT/'assets/source/combat/companion_animations'
OUTPUT = ROOT/'assets/combat'
COMMON = {
    'idle': ([0, 1, 2, 3], [180]*4, True),
    'attack': ([4, 5, 6, 7], [160, 180, 120, 260], False),
    'guard': ([12, 13], [240, 240], True),
    'hurt': ([14, 15], [160, 240], False),
    'victory': ([16, 17], [340, 340], True),
    'defeat': ([18, 19], [260, 420], False),
    'walk': ([20, 21, 22, 23], [140]*4, True),
}
SPECIAL = ([8, 9, 10, 11], [220, 280, 160, 240], False)
NAMES = {'lucan': 'Lucan Rooke', 'rhea': 'Rhea Sorel'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ground_point(cutout, bounds):
    """Register boots rather than the equipment-weighted alpha centroid.

    Brown boot interiors distinguish feet from Rhea's purple staff/green dress
    and Lucan's silver sword. An explicit source landmark may override this in
    recipe.json when a pose occludes its boots.
    """
    width, height = cutout.size
    pixels = cutout.load()
    points = [(x, y) for y in range(max(0, height-round(height*.2)), height)
              for x in range(width)
              if pixels[x, y][3] and pixels[x, y][0] > pixels[x, y][1]+8
              and pixels[x, y][1] > pixels[x, y][2]+5]
    if not points:
        raise ValueError('A pose needs an explicit ground landmark')
    return [bounds[0]+median(x for x, y in points),
            bounds[1]+max(y for x, y in points)+1]


def build_actor(actor, output_root=None):
    if actor not in NAMES:raise ValueError('Unknown companion')
    folder = SOURCE/actor
    source = folder/'atlas_generated.png'
    recipe_path = folder/'recipe.json'
    recipe = json.loads(recipe_path.read_text()) if recipe_path.exists() else {}
    with Image.open(source) as opened:
        cells = authored_cells(opened.convert('RGBA'), (4, 6))
    grounds = []
    for index, (cutout, center, record) in enumerate(cells):
        grounds.append(recipe.get('ground_points', {}).get(str(index)) or
                       ground_point(cutout, record['source_bounds']))
    heights = [grounds[i][1]-cells[i][2]['source_bounds'][1] for i in range(4)]
    scale = recipe.get('native_scale', 42/median(heights))
    if not isinstance(scale, (int, float)) or not 0 < scale <= 1:
        raise ValueError('Invalid native scale')
    frames, records = [], []
    for index, (cutout, center, record) in enumerate(cells):
        left, top, right, bottom = record['source_bounds']
        ground = grounds[index]
        cutout = cutout.resize((max(1, round(cutout.width*scale)),
                                max(1, round(cutout.height*scale))), Image.Resampling.NEAREST)
        position = [round(32-(ground[0]-left)*scale), round(54-(ground[1]-top)*scale)]
        frame = Image.new('RGBA', (64, 64))
        frame.alpha_composite(cutout, position)
        box = frame.getbbox()
        # Check before composite too: alpha_composite clips out-of-canvas pixels.
        if (position[0] < 1 or position[1] < 1
                or position[0]+cutout.width > 63 or position[1]+cutout.height > 63
                or box is None):
            raise ValueError(f'{actor} pose {index} clips at fixed scale {scale:.5f}: {position}, {cutout.size}')
        frames.append(frame)
        records.append({**record, 'source_ground': ground, 'position': position})
    if len({image.tobytes() for image in frames}) != 24:
        raise ValueError('Expected 24 distinct authored poses')
    states = dict(COMMON)
    special = 'cast' if actor == 'rhea' else 'technique'
    states[special] = SPECIAL
    directory = (Path(output_root) if output_root is not None else OUTPUT)/actor
    directory.mkdir(parents=True, exist_ok=True)
    animations = {}
    for state, (indices, durations, loop) in states.items():
        entries = []
        for number, (index, duration) in enumerate(zip(indices, durations), 1):
            filename = f'{state}_{number:02d}.png'
            frames[index].save(directory/filename, optimize=True)
            entries.append({'file': filename, 'duration_ms': duration, **records[index]})
        animations[state] = {'loop': loop, 'frames': entries}
        if state in ('attack', special):
            animations[state]['contact_ms'] = 360 if state == 'attack' else 500
    animations['flee'] = animations['walk']
    sheet = Image.new('RGBA', (256, 384))
    for index, frame in enumerate(frames):
        sheet.alpha_composite(frame, ((index%4)*64, (index//4)*64))
    sheet.save(directory/'spritesheet.png', optimize=True)
    metadata = {
        'version': 1, 'actor': actor, 'display_name': NAMES[actor],
        'status': 'review', 'animation_set': 'full_combat_review',
        'canvas': [64, 64], 'anchor': [32, 54], 'facing': 'left',
        'source_sheet': source.relative_to(ROOT).as_posix(),
        'source_sha256': digest(source), 'source_grid': [4, 6],
        'native_scale': scale, 'authored_pose_count': 24,
        'image': 'idle_01.png', 'sheet': 'spritesheet.png',
        'animations': animations,
        'extraction': 'Authored alpha cells; one native scale; boot/ground registration; no pose repainting',
    }
    (directory/'animation.json').write_text(json.dumps(metadata, indent=2)+'\n')
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--actor', choices=('lucan', 'rhea', 'all'), default='all')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    actors = NAMES if args.actor == 'all' else [args.actor]
    for actor in actors:
        result = build_actor(actor, args.output)
        print(actor, result['authored_pose_count'], result['native_scale'])


if __name__ == '__main__':
    main()
