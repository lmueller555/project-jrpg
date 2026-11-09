"""Compile the live Sanctuary Cave as one continuous native-pixel dungeon.

The retained source recipe owns room geometry, both reconnecting exploration
loops, interaction approaches and encounter reservations. Collision, walls,
water, crystal sockets and the whole-dungeon map derive from that same recipe.
The earlier three-section exports remain historical inputs, never live scenes.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/maps/sanctuary_cave/recipe.json'
OUTPUT = ROOT/'assets/maps/sanctuary_cave'


def encoded(image):
    stream = BytesIO()
    image.save(stream, format='PNG')
    return stream.getvalue()


def products():
    spec = json.loads(SOURCE.read_text())
    used, output = {SOURCE}, {}

    def read(name):
        path = ROOT/name
        used.add(path)
        return json.loads(path.read_text())

    image_cache = {}
    def opened(name):
        if name not in image_cache:
            path = ROOT/name
            used.add(path)
            with Image.open(path) as image:
                image_cache[name] = image.convert('RGBA')
        return image_cache[name]

    def emit(name, image):
        path = (OUTPUT/name).relative_to(ROOT).as_posix()
        output[path] = encoded(image)
        return path

    packs = {name: read(path) for name, path in spec['manifests'].items()}
    w, h = (value*24 for value in spec['size_tiles'])
    materials = {name: [opened(path) for path in record['tiles']]
                 for name, record in packs['base']['materials'].items()}
    materials['earth'] = [opened(path) for path in packs['geology']['materials']['earth']['tiles']]
    def material(name):
        result = Image.new('RGBA', (w, h))
        tiles = materials[name]
        for y in range(0, h, 24):
            for x in range(0, w, 24):
                index = (x//24*137+y//24*271+spec['seed']) % len(tiles)
                result.alpha_composite(tiles[index], (x, y))
        return result

    floor = Image.new('L', (w, h))
    fd = ImageDraw.Draw(floor)
    for room in spec['rooms']:
        fd.polygon([tuple(p) for p in room['polygon']], fill=255)
    for route in spec['corridors']:
        points = [tuple(p) for p in route['points']]
        fd.line(points, fill=255, width=route['width'])
        radius = route['width']//2
        for x, y in points:
            fd.ellipse((x-radius, y-radius, x+radius, y+radius), fill=255)
    ground = material('dry')
    bayer = np.array(((0, 8, 2, 10), (12, 4, 14, 6),
                      (3, 11, 1, 9), (15, 7, 13, 5)))
    yy, xx = np.indices((h, w))
    threshold = (bayer[(yy//2) % 4, (xx//2) % 4]+.5)*16
    for patch in spec['material_patches']:
        mask = Image.new('L', (w, h))
        ImageDraw.Draw(mask).polygon([tuple(p) for p in patch['polygon']], fill=255)
        coverage = np.array(mask.filter(ImageFilter.BoxBlur(12)))
        mask = Image.fromarray(np.where(coverage > threshold, 255, 0).astype(np.uint8))
        ground.paste(material(patch['material']), (0, 0), mask)
    surrounding = material('dry').convert('RGB').point(lambda value: round(value*.33)).convert('RGBA')
    surrounding.paste(ground, (0, 0), floor)
    ground = surrounding
    # The same modular native wall profiles used throughout the expanded pack
    # are sampled along every northern contour, including the winding passages.
    faces = [opened(packs['base']['modules'][f'wall.front.{i}']['frames'][0]) for i in range(6)]
    fp, gp = floor.load(), ground.load()
    for x in range(w):
        for bottom in [y for y in range(1, h) if fp[x, y] and not fp[x, y-1]]:
            face = faces[x//96 % 6]
            for y in range(max(0, bottom-64), bottom):
                if fp[x, y]:
                    continue
                pixel = face.getpixel((x % 96, y-bottom+64))
                if pixel[3]:
                    gp[x, y] = pixel
    lip = ImageChops.subtract(floor, floor.filter(ImageFilter.MinFilter(5)))
    ground.paste((61, 65, 57, 255), (0, 0, w, h), lip)
    collision = ImageChops.invert(floor)
    water_mask = Image.new('L', (w, h))
    entities, solids, placed, water_records = [], [], [], []

    def module(pack, name):
        if pack == 'keeper':
            record = {'frames': ['assets/terrain/eldenmere/sanctuary_charm/props/flagstones.png'],
                      'anchor': [32, 16], 'footprints': []}
        else:
            record = dict(packs[pack]['modules'][name])
        images = [opened(path) for path in record['frames']]
        record.setdefault('anchor', [images[0].width//2, images[0].height-4])
        return record, images

    def add_entity(identifier, record, position, sort_y, **extra):
        value = {'id': identifier, 'position': list(position), 'frames': record['frames'],
                 'sort_y': sort_y, 'sort_priority': 0,
                 'frame_duration_ms': record.get('frame_duration_ms', 700),
                 'phase_offset': 0, 'reduced_motion_frame': record.get('reduced_motion_frame', 0),
                 **extra}
        entities.append(value)
        return value

    def physical(identifier, record, position, enabled=True):
        rectangles = []
        if enabled:
            for x, y, width, height in record.get('footprints', []):
                x, y = x+position[0], y+position[1]
                ImageDraw.Draw(collision).rectangle((x, y, x+width-1, y+height-1), fill=255)
                rectangles.append([x, y, width, height])
                solids.append({'id': identifier+':'+str(len(rectangles)),
                               'position': [x+width//2, y+height//2]})
        return rectangles

    def water_collision(record, position):
        for x, y, width, height in record.get('water_regions', []):
            x, y = x+position[0], y+position[1]
            ImageDraw.Draw(water_mask).rectangle((x, y, x+width-1, y+height-1), fill=255)

    cells = {tuple(point) for point in spec['pool_cells']}
    for index, (x, y) in enumerate(sorted(cells, key=lambda p: (p[1], p[0]))):
        n, e, s, west = ((x, y-1) not in cells, (x+1, y) not in cells,
                         (x, y+1) not in cells, (x-1, y) not in cells)
        if n and e: key = 'bank.outer_ne.0'
        elif e and s: key = 'bank.outer_se.0'
        elif s and west: key = 'bank.outer_sw.0'
        elif west and n: key = 'bank.outer_nw.0'
        elif n: key = 'bank.north.0'
        elif e: key = 'bank.east.0'
        elif s: key = 'bank.south.0'
        elif west: key = 'bank.west.0'
        elif (x+1, y-1) not in cells: key = 'bank.inner_ne.0'
        elif (x+1, y+1) not in cells: key = 'bank.inner_se.0'
        elif (x-1, y+1) not in cells: key = 'bank.inner_sw.0'
        elif (x-1, y-1) not in cells: key = 'bank.inner_nw.0'
        else: key = 'water.deep.'+str((x*17+y*31+x*y*7) % 3)
        record, images = module('water', key)
        position = [x*24, y*24]
        ground.alpha_composite(images[0], tuple(position))
        identifier = 'water_tile_'+str(index)
        add_entity(identifier, record, position, -100, source_module=key,
                   source_pack='water', water=True, phase_offset=(x*7+y*11) % 6)
        water_collision(record, position)
        water_records.append({'entity_id': identifier, 'module': key, 'position': position})

    for item in spec['placements']:
        record, images = module(item['pack'], item['module'])
        feet = item['position']
        position = [feet[0]-record['anchor'][0], feet[1]-record['anchor'][1]]
        ground_piece = item.get('ground') or item['module'].startswith(('ramp.', 'steps.', 'shelf.'))
        footprints = physical(item['id'], record, position, item.get('collision', True))
        if ground_piece:
            ground.alpha_composite(images[0], tuple(position))
            if item['module'].startswith('shelf.'):
                # Top surfaces remain walkable ground; the front lip sorts in
                # front of the actor while the ramp enters its open notch.
                face = Image.new('RGBA', images[0].size)
                cutoff = images[0].height-24
                face.alpha_composite(images[0].crop((0, cutoff, face.width, face.height)), (0, cutoff))
                path = emit('props/'+item['id']+'_lip.png', face)
                add_entity(item['id']+'_lip', {'frames': [path]}, position, feet[1])
        else:
            add_entity(item['id'], record, position, feet[1], source_module=item['module'],
                       source_pack=item['pack'], footprints=footprints)
        placed.append({'id': item['id'], 'pack': item['pack'], 'module': item['module'],
                       'position': position, 'feet': feet, 'ground': bool(ground_piece)})

    for treasure in spec['treasures']:
        kind = treasure['kind']
        closed, images = module('containers', kind+'.closed')
        opened_record, _ = module('containers', kind+'.open')
        cx, cy = treasure['position']
        position = [cx-20, cy-31]
        record = add_entity(treasure['id'], closed, position, cy+2, state='closed',
                            state_images={'closed': closed['frames'][0], 'open': opened_record['frames'][0]},
                            source_pack='containers', source_module=kind+'.closed')
        footprint = [cx-14, cy-5, 28, 10]
        record['footprint'] = footprint
        ImageDraw.Draw(collision).rectangle((footprint[0], footprint[1], footprint[0]+27, footprint[1]+9), fill=255)
        solids.append({'id': treasure['id'], 'position': [cx, cy]})

    # Ledge faces extend into the surrounding rock, leaving precisely the
    # central 48 px ramp notch as the only entrance to the higher shelf.
    for barrier in spec.get('collision_barriers', []):
        x, y, width, height = barrier['rect']
        ImageDraw.Draw(collision).rectangle((x, y, x+width-1, y+height-1), fill=255)
    collision = ImageChops.lighter(collision, water_mask)
    solid = np.array(collision) != 0
    def free(point):
        x, y = map(round, point)
        return 12 <= x < w-12 and 6 <= y < h-6 and not solid[y-6:y+6, x-12:x+12].any()

    def nearest_free(point):
        if free(point):
            return list(point)
        x, y = point
        candidates = [(dx, dy) for dy in range(-100, 101, 4) for dx in range(-100, 101, 4)]
        candidates.sort(key=lambda delta: delta[0]**2+delta[1]**2)
        return next(([x+dx, y+dy] for dx, dy in candidates if free((x+dx, y+dy))), None)

    # Every grain is embedded in actual rock. Find the closest valid native
    # seam socket using summed-area floor queries; several fields share a
    # region source so the lighting cache stays bounded for the entire level.
    floor_values = np.array(floor, dtype=np.int32)//255
    integral = np.pad(floor_values.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    def contains_floor(x, y, width, height):
        if x < 0 or y < 0 or x+width > w or y+height > h:
            return True
        return bool(integral[y+height, x+width]-integral[y, x+width]-integral[y+height, x]+integral[y, x])
    lights, gems = [], []
    patterns = ['dense', 'diagonal_left', 'sparse', 'corner_outer', 'vertical', 'diagonal_right']
    used_sockets = []
    for index, item in enumerate(spec['light_groups']):
        source = nearest_free(item['near'])
        if source is None:
            raise ValueError('No free light root: '+item['id'])
        color = item['color']
        if isinstance(color, str):
            rgb = packs['micro']['modules'][f'micro.{color}.dense']['color']
        else:
            rgb = color
        light = {'id': item['id'], 'position': source, 'color': rgb, 'radius': item['radius'],
                 'gain': item.get('gain', .45), 'phase': item.get('phase', 0),
                 'steady': item.get('steady', False)}
        lights.append(light)
        if item.get('steady'):
            continue
        field_patterns = item.get('patterns', [patterns[(index+variation*2) % len(patterns)] for variation in range(2)])
        if not isinstance(field_patterns,list) or not 1 <= len(field_patterns) <= 4 or any(pattern not in patterns for pattern in field_patterns):
            raise ValueError('Invalid microcrystal field patterns: '+item['id'])
        for variation,pattern in enumerate(field_patterns):
            key = 'micro.'+color+'.'+pattern
            record, images = module('micro', key)
            anchor = record['anchor']
            candidates = [(dx, dy) for dy in range(-240, 241, 6) for dx in range(-240, 241, 6)]
            bias_x = -24 if variation == 0 else 24
            candidates.sort(key=lambda delta: (delta[0]-bias_x)**2+delta[1]**2)
            position = None
            for dx, dy in candidates:
                candidate = [source[0]+dx-anchor[0], source[1]+dy-anchor[1]]
                center = [candidate[0]+anchor[0], candidate[1]+anchor[1]]
                if any((center[0]-x)**2+(center[1]-y)**2 < 45**2 for x, y in used_sockets):
                    continue
                if all(not contains_floor(candidate[0]+x, candidate[1]+y, width, height)
                       for x, y, width, height in record['core_components']):
                    position = candidate
                    used_sockets.append(center)
                    break
            if position is None:
                raise ValueError('No rock microcrystal socket: '+item['id'])
            identifier = item['id']+'_micro_'+str(variation)
            center = [position[0]+anchor[0], position[1]+anchor[1]]
            add_entity(identifier, record, position, center[1], source_module=key,
                       source_pack='micro', light_index=index, wall_gem_color=color)
            ex, ey, ew, eh = record['emission_bounds']
            gems.append({'id': identifier, 'entity_id': identifier, 'color': color,
                         'position': center, 'light_index': index, 'light_position': source,
                         'crystal_count': record['crystal_count'], 'crystal_sizes': record['crystal_sizes'],
                         'emission_bounds': [position[0]+ex, position[1]+ey, ew, eh]})
        light['entity_id'] = item['id']+'_micro_0'
    # Extra native seam drawings share existing light roots. Their explicit
    # perimeter targets cover every room wall without expanding the32-root
    # lighting cache or making large floor crystals stand in for wall detail.
    group_indices = {item['id']:index for index,item in enumerate(spec['light_groups'])}
    for item in spec.get('wall_fields', []):
        index = group_indices[item['light_group']]
        color = item['color']
        key = 'micro.'+color+'.'+item['pattern']
        record,images = module('micro',key)
        anchor = record['anchor']
        if record['color'] != lights[index]['color']:
            raise ValueError('Wall seam must share its own color light: '+item['id'])
        candidates = [(dx,dy) for dy in range(-96,97,4) for dx in range(-96,97,4)]
        candidates.sort(key=lambda delta:delta[0]**2+delta[1]**2)
        position = None
        for dx,dy in candidates:
            center = [item['near'][0]+dx,item['near'][1]+dy]
            candidate = [center[0]-anchor[0],center[1]-anchor[1]]
            if any((center[0]-x)**2+(center[1]-y)**2 < 36**2 for x,y in used_sockets):continue
            if all(not contains_floor(candidate[0]+x,candidate[1]+y,width,height)
                   for x,y,width,height in record['core_components']):
                position = candidate;used_sockets.append(center);break
        if position is None:raise ValueError('No perimeter microcrystal socket: '+item['id'])
        add_entity(item['id'],record,position,center[1],source_module=key,
                   source_pack='micro',light_index=index,wall_gem_color=color,
                   source_room=item['room'],wall_side=item['side'])
        ex,ey,ew,eh = record['emission_bounds']
        gems.append({'id':item['id'],'entity_id':item['id'],'color':color,
                     'position':center,'light_index':index,'light_position':lights[index]['position'],
                     'crystal_count':record['crystal_count'],'crystal_sizes':record['crystal_sizes'],
                     'source_room':item['room'],'wall_side':item['side'],
                     'emission_bounds':[position[0]+ex,position[1]+ey,ew,eh]})
    if len(lights) > 32:
        raise ValueError('Continuous dungeon exceeds bounded lighting cache')

    # Authoring mistakes fail the build, before pathfinding can hide a blocked
    # station by silently taking a different route.
    checks = dict(spec['traversal_checks'])
    checks['solid_points'] = checks['solid_points']+solids
    for name, point in spec['navigation_points'].items():
        if not free(point):
            raise ValueError('Blocked full-foot navigation station '+name+': '+str(point))
    for item in spec['treasures']:
        if not free(item['approach']):
            raise ValueError('Blocked treasure approach '+item['id'])
    for item in spec['inspections']+spec['links']:
        if not free(item.get('approach', item['position'])):
            raise ValueError('Blocked interaction approach '+item['id'])
    for name, point in spec['legacy_landings'].items():
        if not free(point):
            raise ValueError('Blocked legacy landing '+name)
    arena_fields = {'id','enemy_id','room','level','battlefield','center','approach','retreat','trigger','status'}
    arena_ids = set()
    room_ids = {room['id'] for room in spec['rooms']}
    for arena in spec.get('elemental_arenas', []):
        if (not isinstance(arena,dict) or set(arena) != arena_fields
                or arena['id'] in arena_ids or arena['room'] not in room_ids
                or arena['status'] != 'story_boss' or type(arena['level']) is not int
                or not 1 <= arena['level'] <= 100):
            raise ValueError('Invalid elemental arena metadata')
        arena_ids.add(arena['id'])
        for key in ('center','approach','retreat'):
            if not free(arena[key]):raise ValueError('Blocked elemental '+key+': '+arena['id'])
        x,y,width,height = arena['trigger']
        if (any(type(value) is not int for value in arena['trigger'])
                or not 0 <= x < x+width <= w or not 0 <= y < y+height <= h
                or not x <= arena['center'][0] < x+width
                or not y <= arena['center'][1] < y+height
                or x <= arena['approach'][0] < x+width and y <= arena['approach'][1] < y+height):
            raise ValueError('Invalid elemental trigger: '+arena['id'])
    for name, route in spec['routes'].items():
        for start, end in zip(route, route[1:]):
            distance = max(abs(end[0]-start[0]), abs(end[1]-start[1]))
            for step in range(distance+1):
                point = [start[0]+(end[0]-start[0])*step/max(1, distance),
                         start[1]+(end[1]-start[1])*step/max(1, distance)]
                if not free(point):
                    raise ValueError('Blocked full-foot route '+name+': '+str(point))

    emit('ground.png', ground.convert('RGB'))
    emit('collision.png', collision.convert('RGB'))
    emit('water_mask.png', water_mask.convert('RGB'))
    overview = ground.copy()
    for record in sorted(entities, key=lambda value: (value['sort_y'], value.get('sort_priority', 0))):
        raw = output.get(record['frames'][0])
        image = Image.open(BytesIO(raw)).convert('RGBA') if raw else opened(record['frames'][0])
        overview.alpha_composite(image, tuple(record['position']))
    emit('overview.png', overview.convert('RGB'))
    landmarks = [{'id': room['id'], 'name': room['name'], 'position': spec['navigation_points'][room['id']],
                  'description': room['description']} for room in spec['rooms']]
    data = {'id': spec['id'], 'name': spec['name'], 'kind': 'sanctuary_cave', 'tile_size': 24,
            'size_tiles': spec['size_tiles'], 'size_pixels': [w, h], 'player_probe_size': [24, 12],
            'player_draw_anchor': [12, 30], 'spawn': spec['spawn'],
            'ground_frames': [(OUTPUT/'ground.png').relative_to(ROOT).as_posix()],
            'ground_frame_duration_ms': 700, 'collision': (OUTPUT/'collision.png').relative_to(ROOT).as_posix(),
            'overview': (OUTPUT/'overview.png').relative_to(ROOT).as_posix(),
            'entities': entities, 'foreground': [], 'doors': [], 'npcs': [], 'landmarks': landmarks,
            'cave': {'ambient': [112, 119, 127], 'lights': lights, 'pulse_period_ms': 6000,
                     'wall_gems': gems, 'microcrystal_count': sum(gem['crystal_count'] for gem in gems),
                     'placed_modules': placed, 'water_tiles': water_records,
                     **{key: spec[key] for key in ('rooms', 'routes', 'navigation_points', 'treasures', 'loops',
                                                   'legacy_landings', 'encounter_spaces', 'arena', 'elemental_arenas', 'links', 'inspections')},
                     'traversal_checks': checks},
            'build': {'tool': 'tools/build_continuous_sanctuary_cave.py',
                      'source_recipe': SOURCE.relative_to(ROOT).as_posix(),
                      'source_sha256': {str(path.relative_to(ROOT)): sha256(path.read_bytes()).hexdigest()
                                        for path in sorted(used)}}}
    output[(OUTPUT/'map.json').relative_to(ROOT).as_posix()] = (json.dumps(data, indent=2, ensure_ascii=False)+'\n').encode()
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    changed = []
    result = products()
    for name, raw in result.items():
        path = ROOT/name
        if not path.exists() or path.read_bytes() != raw:
            changed.append(name)
            if not args.check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
    if args.check and changed:
        raise SystemExit('Stale continuous cave exports: '+', '.join(changed))
    print(('Verified' if args.check else 'Built')+f' {len(result)} continuous cave exports')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
