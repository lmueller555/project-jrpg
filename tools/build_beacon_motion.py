"""Export authored walking and mechanical-repair frames for the opening.

The imagegen masters remain unchanged. This build step crops each isolated
cell, cleans its transparent matte, applies one physical scale per authored
actor/sheet, and registers the boot baseline. It never deforms anatomy.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/cinematics/beacon_motion'
TARGET = ROOT/'assets/story/opening_cinematic/actors/beacon_motion'
CANVAS = (96, 112)
ANCHOR = (48, 104)
WALK_FILE = 'walk_left_generated.png'
REPAIR_FILE = 'mira_repair_generated.png'
WALK_SCALES = {'caelan': 80/431, 'mira': 80/417}
REPAIR_SCALE = 80/485
REPAIR_NAMES = ('stand_right', 'repair_lower', 'repair_prepare',
                'repair_work_01', 'repair_work_02', 'repair_finish')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bounds_in_cell(source, cell):
    image = source.crop(cell)
    alpha = np.asarray(image.getchannel('A'))
    ys, xs = np.nonzero(alpha >= 128)
    if not len(xs):
        raise ValueError('An authored motion cell is empty')
    return (int(xs.min())+cell[0], int(ys.min())+cell[1],
            int(xs.max()+1)+cell[0], int(ys.max()+1)+cell[1])


def export(source, bounds, scale):
    image = source.crop(bounds)
    pixels = np.array(image)
    pixels[:, :, 3] = np.where(pixels[:, :, 3] >= 128, 255, 0)
    image = Image.fromarray(pixels)
    opaque = pixels[:, :, 3] > 0
    # The entire foot silhouette determines the grounded root; every frame
    # retains its own authored stride while sharing one physical body scale.
    last = opaque[-min(35, len(opaque)):]
    foot = np.flatnonzero(last.any(axis=0))
    center = (int(foot.min())+int(foot.max())+1)/2
    size = (round(image.width*scale), round(image.height*scale))
    image = image.resize(size, Image.Resampling.NEAREST)
    offset = (round(ANCHOR[0]-center*scale), ANCHOR[1]-image.height)
    result = Image.new('RGBA', CANVAS)
    result.alpha_composite(image, offset)
    if result.getbbox() is None or result.getbbox()[3] != ANCHOR[1]:
        raise ValueError('Motion export lost its boot registration')
    return result, {'source_bounds': list(bounds), 'physical_scale': scale,
                    'offset': list(offset), 'bounds': list(result.getbbox())}


def frame_record(filename, duration):
    return {'file': filename, 'duration_ms': duration}


def build():
    TARGET.mkdir(parents=True, exist_ok=True)
    originals = {name: digest(SOURCE/name) for name in (WALK_FILE, REPAIR_FILE)}
    records = {'version': 1, 'canvas': list(CANVAS), 'anchor': list(ANCHOR),
               'exporter': 'tools/build_beacon_motion.py', 'actors': {}}
    review = Image.new('RGB', (96*6, 112*3), '#28313b')
    draw = ImageDraw.Draw(review)
    walk = Image.open(SOURCE/WALK_FILE).convert('RGBA')
    for row, actor in enumerate(('caelan', 'mira')):
        folder = TARGET/actor
        folder.mkdir(exist_ok=True)
        poses, extraction, exported = {}, {}, []
        top, bottom = (0, 535) if row == 0 else (535, walk.height)
        for column in range(4):
            cell = (round(column*walk.width/4), top,
                    round((column+1)*walk.width/4), bottom)
            source_bounds = bounds_in_cell(walk, cell)
            image, details = export(walk, source_bounds, WALK_SCALES[actor])
            name = f'walk_left_{column+1:02d}'
            filename = name+'.png'
            image.save(folder/filename)
            relative = f'../beacon_motion/{actor}/{filename}'
            poses['beacon_'+name] = relative
            extraction['beacon_'+name] = dict(details,
                source=f'assets/source/cinematics/beacon_motion/{WALK_FILE}',
                sha256=digest(folder/filename))
            exported.append(relative)
            review.paste(image, (column*96, row*112), image)
            draw.text((column*96+2, row*112+1), actor+' '+str(column+1), fill='#eeeeee')
        poses['walk_left'] = exported[0]
        records['actors'][actor] = {'poses': poses,
            'loops': {'walk_left': [frame_record(f, 180) for f in exported]},
            'transitions': {}, 'extraction': extraction,
            'sources': [{'path': f'assets/source/cinematics/beacon_motion/{WALK_FILE}',
                         'sha256': originals[WALK_FILE],
                         'native_scale': WALK_SCALES[actor]}]}
    repair = Image.open(SOURCE/REPAIR_FILE).convert('RGBA')
    mira = records['actors']['mira']
    for index, name in enumerate(REPAIR_NAMES):
        row, column = divmod(index, 3)
        top, bottom = (0, 570) if row == 0 else (570, repair.height)
        cell = (column*512, top, (column+1)*512, bottom)
        source_bounds = bounds_in_cell(repair, cell)
        image, details = export(repair, source_bounds, REPAIR_SCALE)
        filename = name+'.png'
        image.save(TARGET/'mira'/filename)
        relative = '../beacon_motion/mira/'+filename
        mira['poses']['beacon_'+name] = relative
        mira['extraction']['beacon_'+name] = dict(details,
            source=f'assets/source/cinematics/beacon_motion/{REPAIR_FILE}',
            sha256=digest(TARGET/'mira'/filename))
        review.paste(image, (index*96, 224), image)
        draw.text((index*96+2, 225), name, fill='#eeeeee')
    mira['poses']['repair'] = mira['poses']['beacon_repair_work_01']
    mira['loops']['repair'] = [
        frame_record(mira['poses']['beacon_repair_work_01'], 240),
        frame_record(mira['poses']['beacon_repair_work_02'], 240),
        frame_record(mira['poses']['beacon_repair_work_01'], 240),
        frame_record(mira['poses']['beacon_repair_prepare'], 180)]
    lowering = [frame_record(mira['poses']['beacon_stand_right'], 140),
                frame_record(mira['poses']['beacon_repair_lower'], 200),
                frame_record(mira['poses']['beacon_repair_prepare'], 180)]
    mira['transitions']['walk_left:repair'] = lowering
    mira['transitions']['stand:repair'] = lowering
    mira['transitions']['repair:stand'] = [
        frame_record(mira['poses']['beacon_repair_finish'], 200),
        frame_record(mira['poses']['beacon_repair_lower'], 220),
        frame_record(mira['poses']['beacon_stand_right'], 180)]
    mira['sources'].append({'path': f'assets/source/cinematics/beacon_motion/{REPAIR_FILE}',
                            'sha256': originals[REPAIR_FILE],
                            'native_scale': REPAIR_SCALE})
    for name, original in originals.items():
        if digest(SOURCE/name) != original:
            raise AssertionError('An authored source changed during export')
    (TARGET/'manifest_fragment.json').write_text(json.dumps(records, indent=2)+'\n')
    work = ROOT/'work'
    work.mkdir(exist_ok=True)
    review.resize((1152, 672), Image.Resampling.NEAREST).save(work/'beacon-motion-contact.png')
    print('Exported eight left-walk frames and six right-facing repair poses.')
    return records


if __name__ == '__main__':
    build()
