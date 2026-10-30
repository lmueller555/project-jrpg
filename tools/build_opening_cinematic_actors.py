"""Export authored quiet-cinematic sprites without changing their anatomy.

Build dependencies: Pillow, NumPy. Generated source sheets are retained intact.
Each actor uses a single physical scale for every pose; only cropping, removal
of transparent generation haze and alignment to the planted-boot baseline are
performed here. No limb deformation or per-pose body stretching is applied.
"""
from __future__ import annotations

from collections import deque
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/cinematics/opening_actors'
TARGET = ROOT/'assets/story/opening_cinematic/actors'
CANVAS = (96, 112)
ANCHOR = (48, 104)
ACTORS = {
    'caelan': {'file': 'caelan_quiet_generated.png', 'scale': .18,
               'poses': ('seated_empty', 'seated_cup', 'glance', 'drink', 'look_out', 'stand')},
    'mira': {'file': 'mira_quiet_generated.png', 'scale': .167,
             'poses': ('kneel', 'offer', 'sit', 'look', 'stand', 'recover')},
}
SUPPLEMENTS = {
    'caelan': {'file': 'caelan_inbetweens_generated.png', 'scale': .16,
               'poses': ('reach_empty', 'receive_cup', 'withdraw_cup', 'lift_cup', 'rise', 'rise_high')},
    'mira': {'file': 'mira_inbetweens_generated.png', 'scale': .151,
             'poses': ('lift_cup', 'release_cup', 'lower_hands', 'rise_kneel', 'lower_seat', 'settle_seat')},
}
TRANSITIONS = {
    'caelan': {
        'seated_empty:reach_empty': [('reach_empty', 260)],
        'reach_empty:seated_cup': [('receive_cup', 250), ('withdraw_cup', 280)],
        'seated_empty:seated_cup': [('receive_cup', 250), ('withdraw_cup', 280)],
        'seated_cup:drink': [('lift_cup', 260)],
        'drink:seated_cup': [('lift_cup', 260), ('withdraw_cup', 220)],
        'seated_cup:stand': [('rise', 260), ('rise_high', 260)],
    },
    'mira': {
        'kneel:offer': [('lift_cup', 320)],
        'offer:kneel': [('release_cup', 230), ('lower_hands', 260)],
        'offer:recover': [('release_cup', 230), ('lower_hands', 260)],
        'kneel:sit': [('rise_kneel', 220), ('stand', 160), ('recover', 200),
                      ('lower_seat', 220), ('settle_seat', 220)],
        'sit:stand': [('settle_seat', 200), ('lower_seat', 200), ('recover', 200)],
        'look:stand': [('settle_seat', 200), ('lower_seat', 200), ('recover', 200)],
    },
}
DRINKING = {
    'file': 'caelan_drinking_generated.png', 'scale': .134,
    'poses': ('cup_raise_low', 'lift_cup', 'cup_near_mouth', 'drink',
              'lower_cup', 'cup_lower_mid'),
}
DRINKING_TRANSITIONS = {
    'seated_cup:drink': [('cup_raise_low', 160), ('lift_cup', 160),
                        ('cup_near_mouth', 160)],
    'drink:seated_cup': [('lower_cup', 160), ('cup_lower_mid', 160),
                        ('cup_raise_low', 160)],
}


def components(image):
    """Locate the six separated opaque actors, including cells crossing a row."""
    alpha = np.asarray(image.getchannel('A'))
    mask = alpha >= 128
    seen = np.zeros(mask.shape, dtype=np.bool_)
    height, width = mask.shape
    found = []
    for y, x in zip(*np.nonzero(mask)):
        if seen[y, x]:
            continue
        seen[y, x] = True
        queue = deque([(int(x), int(y))])
        left = right = int(x)
        top = bottom = int(y)
        area = 0
        while queue:
            px, py = queue.popleft()
            area += 1
            left, right = min(left, px), max(right, px)
            top, bottom = min(top, py), max(bottom, py)
            for nx, ny in ((px-1, py), (px+1, py), (px, py-1), (px, py+1)):
                if 0 <= nx < width and 0 <= ny < height and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    queue.append((nx, ny))
        if area > 10000:
            found.append((left, top, right+1, bottom+1))
    found.sort(key=lambda b: (int((b[1]+b[3])/2 >= 512), (b[0]+b[2])/2))
    if len(found) != 6:
        raise ValueError(f'Expected six isolated character poses, got {len(found)}')
    return found


def export_pose(image, bounds, scale):
    crop = image.crop(bounds)
    pixels = np.array(crop)
    pixels[:, :, 3] = np.where(pixels[:, :, 3] >= 128, 255, 0)
    crop = Image.fromarray(pixels)
    alpha = pixels[:, :, 3] > 0
    foot = alpha[-min(35, len(alpha)):]
    foot_x = np.flatnonzero(foot.any(axis=0))
    center = (int(foot_x.min()) + int(foot_x.max()) + 1)/2
    scaled = crop.resize((round(crop.width*scale), round(crop.height*scale)), Image.Resampling.NEAREST)
    offset = (round(ANCHOR[0]-center*scale), ANCHOR[1]-scaled.height)
    canvas = Image.new('RGBA', CANVAS)
    canvas.alpha_composite(scaled, offset)
    return canvas, {'source_bounds': list(bounds), 'foot_center_source_x': center,
                    'offset': list(offset), 'bounds': list(canvas.getbbox())}


def build_drinking():
    """Replace only Caelan's drinking action, preserving all other exports."""
    folder = TARGET/'caelan'
    manifest_path = folder/'animation.json'
    metadata = json.loads(manifest_path.read_text(encoding='utf-8'))
    source_path = SOURCE/DRINKING['file']
    source_data = source_path.read_bytes()
    source = Image.open(source_path).convert('RGBA')
    source_name = source_path.relative_to(ROOT).as_posix()
    for pose, bounds in zip(DRINKING['poses'], components(source)):
        frame, details = export_pose(source, bounds, DRINKING['scale'])
        details['source'] = source_name
        filename = pose+'.png'
        frame.save(folder/filename)
        metadata['poses'][pose] = filename
        metadata['extraction'][pose] = details
    metadata['sources'] = [record for record in metadata['sources']
                           if record['path'] != source_name]
    metadata['sources'].append({'path': source_name,
                                'sha256': hashlib.sha256(source_data).hexdigest(),
                                'native_scale': DRINKING['scale']})
    for identifier, frames in DRINKING_TRANSITIONS.items():
        metadata['transitions'][identifier] = [
            {'file': pose+'.png', 'duration_ms': duration} for pose, duration in frames]
    manifest_path.write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')

    work = ROOT/'work'
    work.mkdir(exist_ok=True)
    poses = ('seated_cup', *DRINKING['poses'], 'seated_cup')
    contact = Image.new('RGB', (96*4, 112*2), '#292f3b')
    draw = ImageDraw.Draw(contact)
    for index, pose in enumerate(poses):
        x, y = index%4*96, index//4*112
        frame = Image.open(folder/(pose+'.png')).convert('RGBA')
        contact.paste(frame, (x, y), frame)
        draw.text((x+2, y+1), pose, fill='#eeeeee')
        draw.line((x, y+104, x+95, y+104), fill='#747d83')
    contact.resize((1152, 672), Image.Resampling.NEAREST).save(work/'cinematic-drinking-contact.png')
    sequence = [('seated_cup', 550), ('cup_raise_low', 160), ('lift_cup', 160),
                ('cup_near_mouth', 160), ('drink', 650), ('lower_cup', 160),
                ('cup_lower_mid', 160), ('cup_raise_low', 160), ('seated_cup', 650)]
    frames, durations = [], []
    for pose, duration in sequence:
        frame = Image.open(folder/(pose+'.png')).convert('RGBA')
        preview = Image.new('RGBA', CANVAS, '#292f3b')
        preview.alpha_composite(frame)
        frames.append(preview.convert('RGB').resize((576, 672), Image.Resampling.NEAREST))
        durations.append(duration)
    frames[0].save(work/'cinematic-drinking-preview.gif', save_all=True,
                   append_images=frames[1:], duration=durations, loop=0,
                   disposal=2, optimize=False)
    print('Exported six registered drinking frames; other actor exports unchanged.')


def build():
    all_metadata = {}
    for actor, record in ACTORS.items():
        path = SOURCE/record['file']
        original = path.read_bytes()
        source = Image.open(path).convert('RGBA')
        output = TARGET/actor
        output.mkdir(parents=True, exist_ok=True)
        previous_path = output/'animation.json'
        previous = (json.loads(previous_path.read_text(encoding='utf-8'))
                    if previous_path.exists() else {})
        metadata = {'version': 1, 'actor': actor, 'canvas': list(CANVAS),
                    'anchor': list(ANCHOR), 'native_scale': record['scale'],
                    'source': path.relative_to(ROOT).as_posix(),
                    'source_sha256': hashlib.sha256(original).hexdigest(),
                    'poses': {}, 'extraction': {}, 'transitions': {}}
        metadata['sources'] = []
        for sheet_record in (record, SUPPLEMENTS[actor]):
            sheet_path = SOURCE/sheet_record['file']
            sheet_data = sheet_path.read_bytes()
            sheet = Image.open(sheet_path).convert('RGBA')
            metadata['sources'].append({'path': sheet_path.relative_to(ROOT).as_posix(),
                                        'sha256': hashlib.sha256(sheet_data).hexdigest(),
                                        'native_scale': sheet_record['scale']})
            for pose, bounds in zip(sheet_record['poses'], components(sheet)):
                frame, details = export_pose(sheet, bounds, sheet_record['scale'])
                details['source'] = sheet_path.relative_to(ROOT).as_posix()
                filename = pose+'.png'
                frame.save(output/filename)
                metadata['poses'][pose] = filename
                metadata['extraction'][pose] = details
        for transition, frames in TRANSITIONS[actor].items():
            metadata['transitions'][transition] = [
                {'file': pose+'.png', 'duration_ms': duration} for pose, duration in frames]
        # Selective later-scene exports own additional acting and motion. A
        # base rebuild preserves their records and files instead of silently
        # discarding handholding, empty standing, casting or repair loops.
        for section in ('poses', 'extraction', 'transitions', 'loops'):
            additions = previous.get(section, {})
            if additions:
                metadata[section] = {**additions, **metadata.get(section, {})}
        known_sources = {item['path'] for item in metadata['sources']}
        metadata['sources'].extend(item for item in previous.get('sources', [])
                                   if item['path'] not in known_sources)
        (output/'animation.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
        all_metadata[actor] = metadata
    build_drinking()
    review = Image.new('RGB', (96*6, 112*4), '#292f3b')
    draw = ImageDraw.Draw(review)
    for actor_index, (actor, record) in enumerate(ACTORS.items()):
        for supplement, sheet_record in enumerate((record, SUPPLEMENTS[actor])):
            row = actor_index*2+supplement
            for column, pose in enumerate(sheet_record['poses']):
                frame = Image.open(TARGET/actor/(pose+'.png')).convert('RGBA')
                review.paste(frame, (column*96, row*112), frame)
                draw.text((column*96+2, row*112+1), pose, fill='#eeeeee')
    work = ROOT/'work'
    work.mkdir(exist_ok=True)
    review.resize((1152, 896), Image.Resampling.NEAREST).save(work/'opening-cinematic-actor-contact.png')
    print('Exported twenty-four quiet poses/inbetweens with fixed physical scales and foot anchors.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--drinking-only', action='store_true',
                        help="Rebuild only Caelan's registered lift/sip/lower action")
    arguments = parser.parse_args()
    if arguments.drinking_only:
        build_drinking()
    else:
        build()
