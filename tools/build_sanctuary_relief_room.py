"""Build the Sanctuary's visitor relief room from existing native pixel modules."""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.build_sanctuary_reserve_hall import fantasy_modules

SOURCE = ROOT/'assets/source/terrain/elden_vale_sanctuary_relief/recipe.json'
ART = ROOT/'assets/terrain/elden_vale_sanctuary_relief'
MAP = ROOT/'assets/maps/elden_vale_sanctuary_relief'


def png(image):
    stream = BytesIO()
    image.save(stream, format='PNG')
    return stream.getvalue()


def box(rect):
    x, y, width, height = rect
    return x, y, x+width, y+height


def products():
    data = json.loads(SOURCE.read_text())
    assets = {}
    for name, record in data['assets'].items():
        path = ROOT/record['path']
        if hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError('Source pixel asset changed: '+record['path'])
        with Image.open(path) as source:
            assets[name] = source.convert('RGBA')
    palette = {tuple(bytes.fromhex(key[1:])): tuple(bytes.fromhex(value[1:]))
               for key, value in data['stone_palette'].items()}

    def stone(image):
        result = image.copy()
        colors = []
        for r, g, b, alpha in image.get_flattened_data():
            color = palette.get((r, g, b))
            if color is None and g > r:
                color = (185, 177, 152)
            colors.append((*color, alpha) if color else (r, g, b, alpha))
        result.putdata(colors)
        return result

    ground = Image.new('RGBA', tuple(data['native_size']), '#24302d')
    x, y, width, height = data['floor_rect']
    for row in range(height//24):
        for col in range(width//24):
            ground.alpha_composite(assets['floor_'+'abc'[(col+2*row)%3]],
                                   (x+col*24, y+row*24))
    masonry, cap = stone(assets['stone_front']), stone(assets['stone_back'])
    for rect in data['walls'].values():
        x, y, width, height = rect
        for yy in range(y, y+height, 24):
            for xx in range(x, x+width, 24):
                ground.alpha_composite(masonry.crop((0, 0, min(24, x+width-xx),
                                                     min(24, y+height-yy))), (xx, yy))
    for xx in range(data['native_size'][0]//24):
        ground.alpha_composite(cap.crop((0,0,24,8)), (xx*24,18))
    modules = fantasy_modules(data)
    for point in data['windows']:
        ground.alpha_composite(modules['crystal_window'], tuple(point))
    for record in data['fantasy']['wall_details']:
        ground.alpha_composite(modules[record['module']], tuple(record['position']))
    ex, ey, ew, eh = data['exit_clearance']
    for yy in range(ey, ey+eh, 24):
        for xx in range(ex, ex+ew, 24):
            ground.alpha_composite(assets['floor_a'].crop((0,0,min(24,ex+ew-xx),
                                                          min(24,ey+eh-yy))), (xx,yy))
    for xx in range(ex, ex+ew, 24):
        ground.alpha_composite(assets['threshold'], (xx, ey+6))
    collision = Image.new('L', ground.size, 255)
    collision.paste(0, box(data['floor_rect']))
    collision.paste(0, box(data['exit_clearance']))
    output = {ART/'ground.png': png(ground.convert('RGB'))}
    entities, footprints = [], []
    for record in data['objects']:
        refs = []
        if record.get('kind') == 'water_table':
            image = Image.new('RGBA', (48,56))
            image.alpha_composite(assets['table'], (0,8))
            image.alpha_composite(assets['washbasin'], (12,0))
            refs = ['table', 'washbasin']
        elif 'module' in record:
            image = modules[record['module']]
        else:
            image = assets[record['asset']]
            refs = [record['asset']]
        path = ART/'props'/(record['id']+'.png')
        output[path] = png(image)
        entity = {'id':record['id'], 'position':record['position'],
                  'sort_y':record['sort_y'], 'sort_priority':0,
                  'frames':[path.relative_to(ROOT).as_posix()],
                  'frame_duration_ms':300, 'phase_offset':0,
                  'source_assets':[data['assets'][key]['path'] for key in refs]}
        if 'module' in record:
            entity['source_module'] = record['module']
        if 'floor_rect' in record:
            x, y = record['position']
            dx, dy, width, height = record['floor_rect']
            footprint = [x+dx,y+dy,width,height]
            entity['footprint'] = footprint
            collision.paste(255, box(footprint))
            footprints.append({'id':record['id'],'rect':footprint})
        entities.append(entity)
    overview = ground.copy()
    for entity in sorted(entities, key=lambda item:item['sort_y']):
        image = Image.open(BytesIO(output[ROOT/entity['frames'][0]])).convert('RGBA')
        overview.alpha_composite(image, tuple(entity['position']))
    output[ART/'overview.png'] = png(overview.convert('RGB'))
    output[MAP/'collision.png'] = png(collision)
    map_data = {
        'id':data['id'], 'name':data['name'], 'kind':'interior',
        'size_pixels':data['native_size'],
        'size_tiles':[n//24 for n in data['native_size']], 'tile_size':24,
        'player_probe_size':[24,12], 'player_draw_anchor':[12,30],
        'spawn':data['spawn'],
        'ground_frames':[(ART/'ground.png').relative_to(ROOT).as_posix()],
        'ground_frame_duration_ms':300,
        'overview':(ART/'overview.png').relative_to(ROOT).as_posix(),
        'collision':(MAP/'collision.png').relative_to(ROOT).as_posix(),
        'entities':entities, 'foreground':[], 'npcs':[], 'quests':[], 'landmarks':[],
        'exterior_map_position':data['exterior_map_position'],
        'destinations':data['destinations'], 'public_approaches':data['public_approaches'],
        'inspection_points':data['inspection_points'], 'relief_room':data['relief_room'],
        'doors':[{'id':'hall','anchor':[168,270], 'entry_y':270,
                  'entry_side':'south','entry_half_width':10,
                  'open_radius':30,'close_radius':38, 'frame_duration_ms':100,
                  'frames':[], 'position':[0,0], 'host':None, 'requires_open':False,
                  'destination':'assets/maps/elden_vale_sanctuary_hall/map.json',
                  'spawn':data['hall_return'], 'arrival_facing':'front',
                  'arrival_door':'relief_room'}],
        'source_recipe':SOURCE.relative_to(ROOT).as_posix(),
        'source_recipe_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'source_assets':list(data['assets'].values()), 'authoring':data['authoring'],
        'object_footprints':footprints, 'walkable_floor':data['floor_rect'],
        'exit_clearance':data['exit_clearance'], 'design':data['design']}
    output[MAP/'map.json'] = (json.dumps(map_data, indent=2)+'\n').encode()
    output[ART/'art.json'] = (json.dumps({
        'version':1, 'authoring':data['authoring'],
        'source_recipe':map_data['source_recipe'],
        'source_assets':map_data['source_assets'], 'native_size':data['native_size'],
        'entities':entities, 'design':data['design']}, indent=2)+'\n').encode()
    return output


def build(check=False):
    output = products()
    for path, content in output.items():
        if check:
            if not path.is_file() or path.read_bytes() != content:
                raise ValueError('Stale visitor relief room export: '+str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    print(f'{"Verified" if check else "Exported"} {len(output)} visitor relief room products')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    build(parser.parse_args().check)
