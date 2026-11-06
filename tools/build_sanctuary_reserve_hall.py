"""Export the actor-free reserve hall and its native collision/depth metadata.

The retained image-generation source supplies the artwork. This exporter only
scales it uniformly, cuts matching depth silhouettes and authors navigation.
"""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/terrain/elden_vale_sanctuary_hall/recipe.json'
ART = ROOT/'assets/terrain/elden_vale_sanctuary_hall'
MAP = ROOT/'assets/maps/elden_vale_sanctuary_hall'


def png(image):
    data = BytesIO();image.save(data, format='PNG');return data.getvalue()


def rect_box(rect):
    x,y,w,h = rect;return x,y,x+w,y+h


def products():
    data = json.loads(SOURCE.read_text())
    source = ROOT/data['source']
    if hashlib.sha256(source.read_bytes()).hexdigest() != data['source_sha256']:
        raise ValueError('Retained reserve hall source differs from its recipe')
    image = Image.open(source).convert('RGB')
    if list(image.size) != data['source_size']:raise ValueError('Unexpected source size')
    image = image.resize(tuple(data['native_size']), Image.Resampling.NEAREST)
    output = {ART/'ground.png':png(image), ART/'overview.png':png(image)}
    blocked = Image.new('L', image.size, 255)
    for rect in data['walkable_rects']:blocked.paste(0, rect_box(rect))
    for record in data['solid_rects']:blocked.paste(255, rect_box(record['rect']))
    output[MAP/'collision.png'] = png(blocked)
    entities = []
    ratio = image.width/data['source_size'][0]
    for record in data['depth_props']:
        mask = Image.new('L', image.size)
        polygon = [(round(x*ratio),round(y*ratio)) for x,y in record['source_polygon']]
        ImageDraw.Draw(mask).polygon(polygon, fill=255)
        layer = image.convert('RGBA');layer.putalpha(mask)
        crop = record['native_crop'];layer = layer.crop(rect_box(crop))
        path = ART/'depth'/f'{record["id"]}.png';output[path] = png(layer)
        entities.append({'id':record['id'], 'position':crop[:2],
                         'sort_y':record['sort_y'], 'sort_priority':0,
                         'frames':[path.relative_to(ROOT).as_posix()],
                         'frame_duration_ms':300, 'phase_offset':0})
    map_data = {
        'id':data['id'], 'name':data['name'], 'kind':'interior',
        'size_pixels':data['native_size'], 'size_tiles':[24,16], 'tile_size':24,
        'player_probe_size':[24,12], 'player_draw_anchor':[12,30],
        'spawn':data['spawn'], 'ground_frames':[(ART/'ground.png').relative_to(ROOT).as_posix()],
        'ground_frame_duration_ms':300, 'overview':(ART/'overview.png').relative_to(ROOT).as_posix(),
        'collision':(MAP/'collision.png').relative_to(ROOT).as_posix(),
        'entities':entities, 'foreground':[], 'npcs':[], 'quests':[], 'landmarks':[],
        'exterior_map_position':data['exterior_map_position'],
        'destinations':data['destinations'], 'inspection_points':data['inspection_points'],
        'doors':[{
            'id':'reserve_exit', 'anchor':data['exit_anchor'], 'entry_y':data['exit_anchor'][1],
            'entry_side':'south', 'entry_half_width':22, 'open_radius':30, 'close_radius':38,
            'frame_duration_ms':100, 'frames':[], 'position':[0,0], 'host':None,
            'requires_open':False, 'destination':'assets/maps/elden_vale_sanctuary/map.json',
            'spawn':data['exterior_return'], 'arrival_facing':'front', 'arrival_door':'sanctuary_hall'}],
        'source_recipe':SOURCE.relative_to(ROOT).as_posix(),
        'source_recipe_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'source_sha256':data['source_sha256']}
    output[MAP/'map.json'] = (json.dumps(map_data,indent=2)+'\n').encode()
    return output


def build(check=False):
    output = products()
    for path,content in output.items():
        if check:
            if not path.is_file() or path.read_bytes() != content:
                raise ValueError(f'Stale reserve hall export: {path.relative_to(ROOT)}')
        else:
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
    print(f'{"Verified" if check else "Exported"} {len(output)} reserve hall products')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    build(parser.parse_args().check)
