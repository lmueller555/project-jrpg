"""Export authored guard directions and their matching closed-helmet portrait.

Image generation owns every costume and body pose. This exporter only removes
faint transparent gutter residue, registers full poses and nearest-resizes them.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/characters/road_guards'
TARGET = ROOT/'assets/characters/road_guards'
PORTRAIT = ROOT/'assets/portraits/eldenmere/road_guard_neutral.png'
CANVAS = (40, 44)
ANCHOR = (20, 38)
DIRECTIONS = ('front', 'left', 'right', 'back')
ROW_BOUNDS = ((0, 310), (310, 610), (610, 910), (910, 1240))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def png(image):
    data = io.BytesIO()
    image.save(data, format='PNG', optimize=True)
    return data.getvalue()


def json_bytes(data):
    return (json.dumps(data, indent=2)+'\n').encode()


def portrait_record():
    return {'name': 'Road guard', 'expression': 'neutral',
            'file': 'road_guard_neutral.png',
            'sprite_root': 'assets/characters/road_guards',
            'source': 'assets/source/characters/road_guards/portrait_generated.png',
            'source_rect': [0, 0, 1254, 1254]}


def registered_pose(sheet, column, row):
    top, bottom = ROW_BOUNDS[row]
    left, right = sheet.width*column//4, sheet.width*(column+1)//4
    cell = sheet.crop((left, top, right, bottom)).convert('RGBA')
    cell.putalpha(cell.getchannel('A').point(lambda value: 255 if value >= 128 else 0))
    box = cell.getbbox()
    if box is None:
        raise ValueError('Empty authored guard cell')
    # The original page's rear-gesture cell moves the equipped arm. It is
    # intentionally not requested here; back-facing recognition uses its calm
    # authored idle/breath poses instead of swapping the shield to another hand.
    pose = cell.crop(box)
    feet = cell.crop((box[0], max(box[1], box[3]-12), box[2], box[3])).getbbox()
    if feet is None:
        raise ValueError('Guard pose has no planted boot contact')
    foot_x = box[0]+(feet[0]+feet[2])/2
    scale = 36/267
    size = (round(pose.width*scale), round(pose.height*scale))
    pose = pose.resize(size, Image.Resampling.NEAREST)
    point = (round(ANCHOR[0]-(foot_x-box[0])*scale), ANCHOR[1]-size[1])
    if point[0] < 0 or point[0]+size[0] > CANVAS[0]:
        raise ValueError('Authored guard gesture leaves its registered canvas')
    output = Image.new('RGBA', CANVAS)
    output.alpha_composite(pose, point)
    return output, {'source_cell': [left, top, right, bottom],
                    'alpha_bounds': list(box), 'scale': scale,
                    'registration': list(point)}


def build_outputs():
    sheet = Image.open(SOURCE/'directions_generated.png').convert('RGBA')
    master = Image.open(SOURCE/'portrait_generated.png').convert('RGB')
    if sheet.size != (1269, 1240):
        raise ValueError('Unexpected guard direction source size')
    outputs, poses, clips, registrations = {}, {}, {}, {}
    board = Image.new('RGB', (4*160, 4*196+24), '#203b33')
    draw = ImageDraw.Draw(board)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 11)
    for row, direction in enumerate(DIRECTIONS):
        names = ('idle_'+direction+'_0', 'idle_'+direction+'_1',
                 'gesture_'+direction, 'recover_'+direction)
        for column, name in enumerate(names):
            # Back-view cell2 incorrectly bends the shield arm; omit it and
            # reuse the authored breathing cell, not a mirrored/front-body pose.
            source_column = 1 if direction == 'back' and column == 2 else column
            image, registration = registered_pose(sheet, source_column, row)
            filename = name+'.png'
            path = TARGET/filename
            outputs[path] = png(image)
            poses[name] = filename
            registrations[name] = registration
            board.paste(image.resize((160, 176), Image.Resampling.NEAREST),
                        (column*160, row*196), image.resize((160, 176), Image.Resampling.NEAREST))
            draw.text((column*160+4,row*196+178), name, font=font,fill='#e2e7db')
        idle = [{'file': names[0]+'.png', 'duration_ms': 1050},
                {'file': names[1]+'.png', 'duration_ms': 1050}]
        clips['idle_'+direction] = {'loop': True, 'frames': idle}
        clips['greet_'+direction] = {'loop': False, 'frames': [
            {'file': names[0]+'.png', 'duration_ms': 160},
            {'file': names[2]+'.png', 'duration_ms': 360},
            {'file': names[3]+'.png', 'duration_ms': 220},
            {'file': names[0]+'.png', 'duration_ms': 260}]}
    outputs[SOURCE/'native_review.png'] = png(board)
    outputs[PORTRAIT] = png(master.resize((72,72), Image.Resampling.NEAREST))
    portrait = portrait_record()
    portrait['source_rect'] = [0,0,*master.size]
    meta = {'version': 1, 'id': 'elden_vale_road_guard', 'canvas': list(CANVAS),
            'draw_anchor': list(ANCHOR), 'poses': poses, 'clips': clips,
            'equipment': {'helmet': 'closed silver visor', 'tabard': 'navy and gold',
                          'shield_arm': 'physical left'},
            'portrait_key': 'road_guard', 'portrait': portrait}
    outputs[TARGET/'animation.json'] = json_bytes(meta)
    provenance = {'version': 1, 'exporter': 'tools/build_road_guards.py',
        'sources': {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in
                    (SOURCE/'directions_generated.png', SOURCE/'portrait_generated.png')},
        'registrations': registrations,
        'exports': {p.relative_to(ROOT).as_posix(): sha(data) for p,data in outputs.items()},
        'notes': ['Full authored body poses; no arm-strip rotation or drawn limbs.',
                  'Four separately authored directions preserve physical shield hand.',
                  'Rejected rear gesture cell is never used by the game.',
                  'Planted boots share a common foot anchor; collision footprints unchanged.']}
    outputs[TARGET/'provenance.json'] = json_bytes(provenance)
    return outputs, portrait


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args=parser.parse_args()
    outputs, record=build_outputs()
    if args.check:
        bad=[str(p.relative_to(ROOT)) for p,data in outputs.items()
             if not p.exists() or p.read_bytes()!=data]
        if bad:raise SystemExit('Guard exports differ: '+', '.join(bad))
        manifest=json.loads((ROOT/'assets/portraits/eldenmere/portraits.json').read_text())
        if manifest['portraits'].get('road_guard')!=record:
            raise SystemExit('Guard portrait manifest differs from authored source')
        print(f'Verified {len(outputs)} guard sprite/portrait/provenance exports')
        return
    for path,data in outputs.items():
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    manifest_path=ROOT/'assets/portraits/eldenmere/portraits.json'
    manifest=json.loads(manifest_path.read_text())
    manifest['portraits']['road_guard']=record
    manifest_path.write_bytes(json_bytes(manifest))
    print(f'Exported {len(outputs)} guard sprite/portrait/provenance files')


if __name__=='__main__':main()
