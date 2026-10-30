"""Export authored cup placement, paired handholding and controlled casting.

This selective exporter never rewrites the original poses or drinking action.
Build dependencies are Pillow and NumPy. Only cropping, alpha cleanup, common
sheet scaling and registration are performed; anatomy remains authored art.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from build_opening_cinematic_actors import ANCHOR, CANVAS, components, export_pose

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/cinematics/opening_actors'
ACTORS = ROOT/'assets/story/opening_cinematic/actors'


def source_record(path, scale):
    return {'path': path.relative_to(ROOT).as_posix(),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'native_scale': scale}


def add_source(metadata, record):
    metadata['sources'] = [item for item in metadata.get('sources', [])
                           if item['path'] != record['path']]
    metadata['sources'].append(record)


def record_pose(metadata, actor, pose, frame, details, source):
    filename = pose+'.png'
    frame.save(ACTORS/actor/filename)
    metadata['poses'][pose] = filename
    details['source'] = source
    metadata['extraction'][pose] = details


def clean(image):
    pixels = np.array(image.convert('RGBA'))
    pixels[:, :, 3] = np.where(pixels[:, :, 3] >= 128, 255, 0)
    return Image.fromarray(pixels)


def transition(metadata, identifier, frames):
    metadata['transitions'][identifier] = [
        {'file': metadata['poses'].get(name, name+'.png'), 'duration_ms': duration}
        for name, duration in frames]


def export_cast_and_cup(metadata):
    path = SOURCE/'beacon_caelan_actions_generated.png'
    image = Image.open(path).convert('RGBA')
    bounds = components(image)
    scale = .153
    names = ('cup_set_start', 'cup_set_down', 'cup_set_released',
             'cast_prepare', 'cast_release', 'stand_empty')
    metadata['poses'].pop('cup_set_released', None)
    metadata['extraction'].pop('cup_set_released', None)
    discarded = ACTORS/'caelan/cup_set_released.png'
    if discarded.exists():
        discarded.unlink()
    for name, box in zip(names, bounds):
        if name == 'cup_set_released':
            continue
        frame, details = export_pose(image, box, scale)
        record_pose(metadata, 'caelan', name, frame, details, path.relative_to(ROOT).as_posix())
    metadata['poses']['cast_recover'] = metadata['poses']['cast_prepare']
    metadata['extraction']['cast_recover'] = dict(metadata['extraction']['cast_prepare'])
    add_source(metadata, source_record(path, scale))

    # A separately authored close study places the supported cup lower than
    # the overview sheet. Register the entire unchanged body at the floor.
    close = SOURCE/'beacon_cup_setdown_generated.png'
    image = clean(Image.open(close))
    box = image.getbbox()
    frame, details = export_pose(image, box, .06)
    record_pose(metadata, 'caelan', 'cup_set_down', frame, details,
                close.relative_to(ROOT).as_posix())
    add_source(metadata, source_record(close, .06))

    transition(metadata, 'seated_cup:cup_set_start', [('cup_set_start', 180)])
    transition(metadata, 'cup_set_down:seated_empty', [('seated_empty', 180)])
    transition(metadata, 'cast_prepare:cast_release', [('cast_prepare', 180)])
    transition(metadata, 'cast_recover:stand_empty', [('cast_recover', 180)])


def export_hands(metadata):
    path = SOURCE/'beacon_handhold_generated.png'
    sheet = Image.open(path).convert('RGBA')
    scale = .145
    names = ('hands_reach', 'hands_meet', 'hands_hold', 'hands_release')
    geometry = {}
    for index, pose in enumerate(names):
        column, row = index%2, index//2
        cell_box = (column*768, row*512, (column+1)*768, (row+1)*512)
        cell = clean(sheet.crop(cell_box))
        alpha = np.asarray(cell.getchannel('A')) > 0
        ys, _ = np.nonzero(alpha)
        bottom = int(ys.max())+1
        foot = alpha[max(0, bottom-30):bottom]
        centers = []
        for left, right in ((0, 384), (384, 768)):
            xs = np.flatnonzero(foot[:, left:right].any(axis=0))+left
            centers.append((float(xs.min())+float(xs.max())+1)/2)
        pair_center = sum(centers)/2
        offset = (round(75.5-pair_center*scale), round(104-bottom*scale))
        scaled = cell.resize((round(768*scale), round(512*scale)), Image.Resampling.NEAREST)
        paired = Image.new('RGBA', (160, 112))
        paired.alpha_composite(scaled, offset)
        geometry[pose] = {'floor_centers': [round(offset[0]+x*scale, 2) for x in centers],
                          'source_foot_centers': centers, 'pair_offset': list(offset)}
        # The paired source deliberately contains shared hand contact. Divide
        # it at that contact seam; drawing both pieces reconstructs the exact
        # authored interaction without arm stretching or duplicated fingers.
        for actor, crop_start, seam_side in (('caelan', 0, 'left'), ('mira', 55, 'right')):
            frame = paired.crop((crop_start, 0, crop_start+96, 112))
            pixels = np.array(frame)
            seam = 74-crop_start
            if seam_side == 'left':
                pixels[:, seam:, 3] = 0
            else:
                pixels[:, :seam, 3] = 0
            frame = Image.fromarray(pixels)
            details = {'source_bounds': list(cell_box), 'bounds': list(frame.getbbox()),
                       'native_scale': scale, 'pair_offset': list(offset),
                       'contact_seam_world_x': 696,
                       'authored_inward_bench_adjustment': True}
            record_pose(metadata[actor], actor, pose, frame, details,
                        path.relative_to(ROOT).as_posix())
    for actor in ('caelan', 'mira'):
        add_source(metadata[actor], source_record(path, scale))
        resting = 'seated_empty' if actor == 'caelan' else 'sit'
        transition(metadata[actor], resting+':hands_reach', [('hands_reach', 180)])
        transition(metadata[actor], 'hands_release:'+resting, [('hands_release', 180)])
    return geometry


def merge_motion(metadata):
    path = ACTORS/'beacon_motion/manifest_fragment.json'
    if not path.exists():
        return
    fragment = json.loads(path.read_text(encoding='utf-8'))
    for actor, additions in fragment['actors'].items():
        for section in ('poses', 'loops', 'transitions', 'extraction'):
            metadata[actor].setdefault(section, {}).update(additions.get(section, {}))
        for record in additions.get('sources', []):
            add_source(metadata[actor], record)
    metadata['mira']['poses']['repair_finish'] = metadata['mira']['poses']['beacon_repair_finish']
    if 'beacon_repair_finish' in metadata['mira']['extraction']:
        metadata['mira']['extraction']['repair_finish'] = dict(metadata['mira']['extraction']['beacon_repair_finish'])


def export_empty_rise(metadata):
    path = SOURCE/'beacon_empty_rise_generated.png'
    image = clean(Image.open(path))
    width = image.width//2
    scale = .113
    for index, pose in enumerate(('rise_empty_01', 'rise_empty_02')):
        cell = image.crop((index*width, 0, (index+1)*width, image.height))
        box = cell.getbbox()
        frame, details = export_pose(cell, box, scale)
        details['source_cell'] = index
        record_pose(metadata, 'caelan', pose, frame, details, path.relative_to(ROOT).as_posix())
    add_source(metadata, source_record(path, scale))
    transition(metadata, 'seated_empty:stand_empty', [('rise_empty_01', 220), ('rise_empty_02', 220)])


def previews():
    work = ROOT/'work'
    work.mkdir(exist_ok=True)
    rows = []
    for actor in ('caelan', 'mira'):
        for pose in ('hands_reach', 'hands_meet', 'hands_hold', 'hands_release'):
            rows.append((actor, pose))
    rows += [('caelan', name) for name in
             ('cup_set_start', 'cup_set_down', 'rise_empty_01', 'rise_empty_02',
              'stand_empty', 'cast_prepare', 'cast_release', 'cast_recover')]
    contact = Image.new('RGB', (96*5, 112*((len(rows)+4)//5)), '#292f3b')
    draw = ImageDraw.Draw(contact)
    for index, (actor, pose) in enumerate(rows):
        frame = Image.open(ACTORS/actor/(pose+'.png' if pose != 'cast_recover' else 'cast_prepare.png'))
        x, y = index%5*96, index//5*112
        contact.paste(frame, (x, y), frame)
        draw.text((x+1, y+1), actor[0]+':'+pose, fill='#eeeeee')
    contact.resize((1440, contact.height*3), Image.Resampling.NEAREST).save(work/'beacon-actor-contact.png')
    frames = []
    durations = []
    for pose, duration in [('hands_reach', 400), ('hands_meet', 400),
                           ('hands_hold', 1300), ('hands_release', 500)]:
        pair = Image.new('RGBA', (160, 112), '#292f3b')
        for actor, x in (('caelan', 0), ('mira', 55)):
            pair.alpha_composite(Image.open(ACTORS/actor/(pose+'.png')).convert('RGBA'), (x, 0))
        frames.append(pair.convert('RGB').resize((960, 672), Image.Resampling.NEAREST))
        durations.append(duration)
    frames[0].save(work/'beacon-handhold-preview.gif', save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, disposal=2, optimize=False)


def build():
    metadata = {actor: json.loads((ACTORS/actor/'animation.json').read_text(encoding='utf-8'))
                for actor in ('caelan', 'mira')}
    export_cast_and_cup(metadata['caelan'])
    export_empty_rise(metadata['caelan'])
    geometry = export_hands(metadata)
    merge_motion(metadata)
    for actor, record in metadata.items():
        (ACTORS/actor/'animation.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    previews()
    (ROOT/'work/beacon-handhold-geometry.json').write_text(json.dumps(geometry, indent=2)+'\n')
    print('Exported authored cup placement, paired handholding, empty standing and controlled casting.')


if __name__ == '__main__':
    build()
