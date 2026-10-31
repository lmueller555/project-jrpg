"""A sparse regional world in global pixels, with bounded chunk residency.

The checked-in region describes terrain as small vector features. Only chunks
touched by a collision query or a viewport are rasterized; no surface, mask or
simulation array has the size of the region. Local town scenes remain separate.
"""
from __future__ import annotations

from collections import OrderedDict
import json
import math
from pathlib import Path

import pygame


ROOT = Path(__file__).resolve().parent
REGION_FILE = ROOT/'assets/maps/overworld/elden_vale/region.json'
ART_FILE = ROOT/'assets/terrain/overworld/elden_vale/art.json'
TILE_SIZE = 24
CHUNK_TILES = 16
CHUNK_PIXELS = TILE_SIZE*CHUNK_TILES
RENDER_BUDGET = 64*1024*1024
VIEW_SIZE = (480, 320)


class _LRU:
    def __init__(self, limit, weigh=None):
        self.limit = max(1, int(limit))
        self.weigh = weigh or (lambda value: 1)
        self.items = OrderedDict()
        self.weight = 0

    def get(self, key):
        if key not in self.items:return None
        self.items.move_to_end(key)
        return self.items[key]

    def put(self, key, value):
        if key in self.items:self.weight -= self.weigh(self.items.pop(key))
        weight = self.weigh(value)
        # Oversized values can serve this request without escaping the budget.
        if weight > self.limit:return value
        self.items[key] = value;self.weight += weight
        while self.weight > self.limit:
            _, removed = self.items.popitem(last=False)
            self.weight -= self.weigh(removed)
        return value

    def clear(self):
        self.items.clear();self.weight = 0


def _point_in_polygon(point, polygon):
    x, y = point;inside = False
    for a, b in zip(polygon, polygon[1:]+polygon[:1]):
        if (a[1] > y) != (b[1] > y):
            crossing = (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]
            if x < crossing:inside = not inside
    return inside


def _distance_to_path(point, points):
    if not points:return math.inf
    if len(points) == 1:return math.dist(point, points[0])
    px, py = point;result = math.inf
    for a, b in zip(points, points[1:]):
        dx, dy = b[0]-a[0], b[1]-a[1]
        squared = dx*dx+dy*dy
        t = 0 if not squared else max(0, min(1, ((px-a[0])*dx+(py-a[1])*dy)/squared))
        result = min(result, math.hypot(px-a[0]-t*dx, py-a[1]-t*dy))
    return result


def _stable_hash(x, y, salt=0):
    """Stable across processes, unlike Python's randomized string hashes."""
    value = (x*0x1f123bb5 ^ y*0x5f356495 ^ salt*0x45d9f3b) & 0xffffffff
    value ^= value >> 16;value = value*0x7feb352d & 0xffffffff
    value ^= value >> 15;value = value*0x846ca68b & 0xffffffff
    return value ^ (value >> 16)


class _BlockedView:
    """Compatibility for old sight queries without exposing a world mask."""
    def __init__(self, world):self.world = world
    def get_at(self, point):return int(self.world.is_blocked_at(point))


class RoadGuard:
    """A fixed regional actor; the travel controller owns guard conversation."""
    def __init__(self, world, gate, position=None, index=0):
        self.data = {'id': f'road_guard:{gate["id"]}:{index}', 'name': 'Road guard'}
        self.position = pygame.Vector2(position or gate['guard_position'])
        self.scene_id = world.data['id']
        self.draw_anchor = (12, 36)
        self.probe_size = (12, 8)
        self.facing = 'front' if self.position.y < 0 else 'back'
        key = 'guard_front' if self.facing == 'front' else 'guard_back'
        self._sprite, self.draw_anchor = world._prop_image(key)
        if self._sprite is None:
            fallback = ROOT/f'assets/characters/npcs/male_01/idle_{self.facing}.png'
            self._sprite = pygame.image.load(str(fallback)).convert_alpha()
            self.draw_anchor = (12, 30)

    @property
    def blocker(self):
        return pygame.Rect(round(self.position.x)-6, round(self.position.y)-4, 12, 8)

    def sprite(self, elapsed_ms):return self._sprite


class OverworldWorld:
    """One world identity across every sparse chunk in the regional manifest."""
    is_overworld = True

    def __init__(self, path=REGION_FILE, progress_flags=(), *,
                 render_budget_bytes=RENDER_BUDGET, collision_cache_limit=64,
                 metadata_cache_limit=64):
        self.path = Path(path).resolve()
        self.region = json.loads(self.path.read_text(encoding='utf-8'))
        if self.region.get('tile_size', TILE_SIZE) != TILE_SIZE:
            raise ValueError('Overworld tiles must use the 24 pixel grid')
        if self.region.get('chunk_size', CHUNK_TILES) != CHUNK_TILES:
            raise ValueError('Overworld chunks must contain 16 by 16 tiles')
        authored_bounds = self.region['bounds_tiles']
        if (len(authored_bounds) != 4 or any(type(n) is not int for n in authored_bounds)
                or authored_bounds[2] <= 0 or authored_bounds[3] <= 0):
            raise ValueError('Overworld bounds must be an integer tile rectangle')
        self.bounds = self._tile_rect(authored_bounds)
        self.size = self.bounds.size
        self.data = {**self.region, 'id': self.region.get('id', 'auratia.overworld'),
                     'kind': 'overworld', 'name': self.region.get('name', 'Elden Vale'),
                     'spawn': self._tile_point(self.region.get('spawn_tile', (12, -25))),
                     'player_probe_size': [24, 12], 'player_draw_anchor': [12, 30],
                     'landmarks': [{**record, 'position': self._tile_point(record['tile_position'])}
                                   for record in self.region.get('landmarks', [])]}
        self.probe_size = (24, 12)
        self._probes = {}
        self._render_cache = _LRU(render_budget_bytes, lambda surface: surface.get_pitch()*surface.get_height())
        self._collision_cache = _LRU(collision_cache_limit)
        self._metadata_cache = _LRU(metadata_cache_limit)
        self._flags = frozenset(progress_flags)
        self._revision = 0
        self._whitelist = (set(map(tuple, self.region['chunk_whitelist']))
                           if 'chunk_whitelist' in self.region else None)
        self.blocked = _BlockedView(self)
        self.doors = [];self.routine_props = [];self.work_fittings = [];self.foreground = []
        self.entities = []
        self._art = {};self._tiles = {};self._props = {}
        self._load_art()
        town = self.region.get('town', {})
        self.town_entry_rect = self._tile_rect(town.get('entry_rect_tiles', (9, -33, 6, 6)))
        self.town_exit = self._tile_point(town.get('exit_tile', self.region.get('spawn_tile', (12, -25))))
        self.gates = []
        for gate in self.region.get('gates', []):
            points = gate.get('guard_tiles', [gate['tile_position']])
            if points and isinstance(points[0], (int,float)):points = [points]
            positions = [self._tile_point(point) for point in points]
            if not positions:positions = [self._tile_point(gate['tile_position'])]
            self.gates.append({**gate, 'position': self._tile_point(gate['tile_position']),
                               'guard_position': positions[0], 'guard_positions': positions,
                               'rect': self._tile_rect(gate['rect_tiles'])})
        self.npcs = [RoadGuard(self, gate, position, index)
                     for gate in self.gates for index,position in enumerate(gate['guard_positions'])]
        self.environment = None
        if self.region.get('detail_art_manifest'):
            from overworld_environment import EnvironmentDetail
            self.environment = EnvironmentDetail(self)

    @staticmethod
    def _tile_point(point):return tuple(value*TILE_SIZE for value in point)

    @staticmethod
    def _tile_rect(rect):return pygame.Rect(*(round(value*TILE_SIZE) for value in rect))

    @property
    def progress_flags(self):return self._flags

    @property
    def cache_stats(self):
        return {'render_bytes': self._render_cache.weight,
                'render_chunks': len(self._render_cache.items),
                'collision_chunks': len(self._collision_cache.items),
                'metadata_chunks': len(self._metadata_cache.items)}

    def set_progress(self, flags):
        flags = frozenset(flags)
        if flags == self._flags:return
        relevant = {gate.get('clearance_flag') for gate in self.gates}
        relevant.add(self.region.get('bridge',{}).get('repair_flag'))
        changed = self._flags.intersection(relevant) != flags.intersection(relevant)
        self._flags = flags
        if not changed:return
        self._revision += 1
        # Geometry is derived from durable facts, never from cache contents.
        self._collision_cache.clear();self._render_cache.clear()

    def _load_art(self):
        candidate = self.region.get('art', self.region.get('art_manifest'))
        path = ROOT/candidate if isinstance(candidate, str) else ART_FILE
        self.art_available = path.exists()
        if self.art_available:self._art = json.loads(path.read_text(encoding='utf-8'))
        detail = self.region.get('detail_art_manifest')
        if detail and (ROOT/detail).exists():
            additional = json.loads((ROOT/detail).read_text(encoding='utf-8'))
            for group in ('tiles','props'):
                self._art.setdefault(group,{}).update(additional.get(group,{}))

    def _tile_image(self, key):
        if key not in self._tiles:
            record = self._art.get('tiles', {}).get(key)
            if record:
                loaded = pygame.image.load(str(ROOT/record['image']))
                surface = loaded.convert_alpha() if key.startswith('water_glint') else loaded.convert()
                if surface.get_size() != (TILE_SIZE, TILE_SIZE):
                    raise ValueError(f'Overworld tile {key} must be 24 by 24 pixels')
            else:
                # Small artless fixtures exercise streaming without a display atlas.
                colors = {'grass':'#66834e', 'dirt':'#a58a5b', 'stone_road':'#b3a58a',
                          'field':'#b2a260', 'forest_floor':'#4b6945', 'water':'#547f89',
                          'bank':'#91a16b', 'scorched':'#65574a', 'wall':'#8d968b'}
                surface = pygame.Surface((TILE_SIZE, TILE_SIZE));surface.fill(colors.get(key, colors['grass']))
            self._tiles[key] = surface
        return self._tiles[key]

    def _prop_image(self, key):
        if key not in self._props:
            record = self._art.get('props', {}).get(key)
            if not record:return None, (0, 0)
            surface = pygame.image.load(str(ROOT/record['image'])).convert_alpha()
            self._props[key] = (surface, tuple(record.get('foot_anchor', (surface.get_width()//2, surface.get_height()))))
        return self._props[key]

    def probe_rect(self, position, size=None):
        width, height = self.probe_size if size is None else size
        return pygame.Rect(round(position[0])-width//2, round(position[1])-height//2, width, height)

    def _has_chunk(self, cx, cy):
        return ((self._whitelist is None or (cx, cy) in self._whitelist)
                and self.bounds.colliderect(pygame.Rect(cx*CHUNK_PIXELS, cy*CHUNK_PIXELS, CHUNK_PIXELS, CHUNK_PIXELS)))

    def _feature_near(self, point, padding=0):
        """Clear roads, banks, landings and scene approaches of decoration."""
        if self.town_entry_rect.inflate(5*TILE_SIZE, 5*TILE_SIZE).collidepoint(self._tile_point(point)):return True
        for clearing in self.region.get('safe_clearings', []):
            rect = self._tile_rect(clearing['rect_tiles']).inflate(2*padding, 2*padding)
            if rect.collidepoint(self._tile_point(point)):return True
        for road in self.region.get('roads', []):
            if _distance_to_path(point, road['points']) < road.get('width', 3)/2+1.3:return True
        for river in self.region.get('terrain', {}).get('rivers', []):
            if _distance_to_path(point, river['points']) < river.get('width', 8)/2+1.3:return True
        for wall in self.region.get('walls', []):
            if wall['x0']-3 <= point[0] <= wall['x1']+3 and abs(point[1]-wall['y']) < 4:return True
        return False

    def _chunk_metadata(self, cx, cy):
        key = (cx, cy);cached = self._metadata_cache.get(key)
        if cached is not None:return cached
        if not self._has_chunk(cx, cy):return None
        if self.environment is not None:
            return self._metadata_cache.put(key,{'coord':key,'props':self.environment.chunk_props(cx,cy)})
        props = []
        # Four-tile cells own their jittered trees, independent of load order.
        for x in range(cx*CHUNK_TILES, (cx+1)*CHUNK_TILES, 4):
            for y in range(cy*CHUNK_TILES, (cy+1)*CHUNK_TILES, 4):
                seed = _stable_hash(x, y)
                point = (x+.5+(seed%25)/10, y+.5+((seed>>5)%25)/10)
                forests = self.region.get('terrain', {}).get('forests', [])
                forest = next((f for f in forests if _point_in_polygon(point, f['polygon'])), None)
                if forest is not None and seed%5 != 0 and not self._feature_near(point):
                    kind = 'tree_conifer' if forest.get('kind') == 'conifer' else 'tree_broadleaf'
                    props.append({'id': f'tree:{x}:{y}', 'key': kind,
                                  'position': self._tile_point(point), 'solid': (12, 8)})
                hills = self.region.get('terrain', {}).get('hills', [])
                if seed%3 == 0 and any(_point_in_polygon(point, h['polygon']) for h in hills) and not self._feature_near(point):
                    # A few peaks distinguish the wooded foothills from fields.
                    kind = 'mountain' if seed%2 == 0 else 'rock'
                    props.append({'id': f'hill:{x}:{y}', 'key': kind,
                                  'position': self._tile_point(point), 'solid': (16, 8)})
        return self._metadata_cache.put(key, {'coord': key, 'props': props})

    @staticmethod
    def _draw_path(surface, color, points, width):
        if not points:return
        width = max(1, round(width))
        # pygame.draw.lines clips the *centre line* to its destination before
        # widening it. A river centred outside a chunk would lose the part of
        # its bank that belongs inside that chunk. Explicit stroke polygons
        # intersect the destination after expansion, for graphics and physics.
        half = width/2
        for a,b in zip(points,points[1:]):
            dx,dy = b[0]-a[0],b[1]-a[1];length = math.hypot(dx,dy)
            if length == 0:continue
            nx,ny = -dy/length*half,dx/length*half
            polygon = [(round(a[0]+nx),round(a[1]+ny)),(round(b[0]+nx),round(b[1]+ny)),
                       (round(b[0]-nx),round(b[1]-ny)),(round(a[0]-nx),round(a[1]-ny))]
            pygame.draw.polygon(surface,color,polygon)
        for point in points:
            pygame.draw.circle(surface,color,(round(point[0]),round(point[1])),width//2)

    def _local_path(self, record, cx, cy):
        ox, oy = cx*CHUNK_PIXELS, cy*CHUNK_PIXELS
        return [(x*TILE_SIZE-ox, y*TILE_SIZE-oy) for x, y in record['points']]

    def _bridge_repaired(self):
        bridge = self.region.get('bridge', {})
        return bool(bridge.get('repair_flag') and bridge['repair_flag'] in self._flags)

    def _bridge_debris(self):
        bridge = self.region.get('bridge')
        if not bridge or self._bridge_repaired():return []
        x,y = bridge['tile_position']
        return [{'key':'rock','position':self._tile_point((x+dx,y+dy)), 'solid':(16,8)}
                for dx,dy in ((11,4),(8,-6),(-18,-2),(-16,6))]

    def _gate_open(self, gate):
        return bool(gate.get('destination_ready') and gate.get('clearance_flag') in self._flags)

    def _wall_segments(self, wall):
        gap = wall.get('gate_width', 0)/2;gate = wall.get('gate_x', wall['x0'])
        if not gap:return [(wall['x0'], wall['x1'])]
        return [(wall['x0'], gate-gap), (gate+gap, wall['x1'])]

    def _collision_chunk(self, cx, cy):
        key = (cx, cy);cached = self._collision_cache.get(key)
        if cached is not None:return cached
        metadata = self._chunk_metadata(cx, cy)
        if metadata is None:return pygame.Mask((CHUNK_PIXELS, CHUNK_PIXELS), fill=True)
        surface = pygame.Surface((CHUNK_PIXELS, CHUNK_PIXELS));surface.fill('black')
        origin = (cx*CHUNK_PIXELS, cy*CHUNK_PIXELS)
        for river in self.region.get('terrain', {}).get('rivers', []):
            self._draw_path(surface, 'white', self._local_path(river, cx, cy), river.get('width', 8)*TILE_SIZE)
        bridge = self.region.get('bridge')
        if bridge:
            if self._bridge_repaired():
                rect = self._tile_rect(bridge.get('deck_rect_tiles', bridge['damage_rect_tiles'])).move(-origin[0], -origin[1])
                pygame.draw.rect(surface, 'black', rect)
            else:
                rect = self._tile_rect(bridge['damage_rect_tiles']).move(-origin[0], -origin[1])
                pygame.draw.rect(surface, 'white', rect)
        for wall in self.region.get('walls', []):
            for left, right in self._wall_segments(wall):
                if right <= left:continue
                rect = self._tile_rect((left, wall['y']-.5, right-left, 1)).move(-origin[0], -origin[1])
                pygame.draw.rect(surface, 'white', rect)
        for gate in self.gates:
            if not self._gate_open(gate):pygame.draw.rect(surface, 'white', gate['rect'].move(-origin[0], -origin[1]))
        props = (self.environment.collision_props(cx,cy) if self.environment is not None
                 else (prop for prop in metadata['props'] if prop.get('solid')))
        for prop in props:
            width, height = prop['solid'];x, y = prop['position']
            rect = pygame.Rect(round(x)-width//2-origin[0], round(y)-height//2-origin[1], width, height)
            pygame.draw.rect(surface, 'white', rect)
        for prop in self._bridge_debris():
            width,height = prop['solid'];x,y = prop['position']
            pygame.draw.rect(surface,'white',pygame.Rect(round(x)-width//2-origin[0],round(y)-height//2-origin[1],width,height))
        mask = pygame.mask.from_threshold(surface, (255,255,255), (1,1,1,255))
        return self._collision_cache.put(key, mask)

    def is_blocked_at(self, point):
        x, y = round(point[0]), round(point[1])
        if not self.bounds.collidepoint(x, y):return True
        cx, cy = x//CHUNK_PIXELS, y//CHUNK_PIXELS
        return bool(self._collision_chunk(cx, cy).get_at((x-cx*CHUNK_PIXELS, y-cy*CHUNK_PIXELS)))

    def can_stand(self, position, size=None, ignore_npc=None, player_blocker=None):
        size = self.probe_size if size is None else tuple(size)
        rect = self.probe_rect(position, size)
        if not self.bounds.contains(rect):return False
        if size not in self._probes:self._probes[size] = pygame.Mask(size, fill=True)
        for cx in range(rect.left//CHUNK_PIXELS, (rect.right-1)//CHUNK_PIXELS+1):
            for cy in range(rect.top//CHUNK_PIXELS, (rect.bottom-1)//CHUNK_PIXELS+1):
                if self._collision_chunk(cx, cy).overlap(self._probes[size], (rect.x-cx*CHUNK_PIXELS, rect.y-cy*CHUNK_PIXELS)) is not None:return False
        return (not any(npc is not ignore_npc and npc.blocker.colliderect(rect) for npc in self.npcs)
                and not any(block.colliderect(rect) for block in getattr(self, 'task_blockers', lambda: ())())
                and (player_blocker is None or not player_blocker.colliderect(rect)))

    def _pattern(self, target, key):
        tile = self._tile_image(key)
        for x in range(0, CHUNK_PIXELS, TILE_SIZE):
            for y in range(0, CHUNK_PIXELS, TILE_SIZE):target.blit(tile, (x, y))

    def _paint_shape(self, target, key, painter):
        overlay = pygame.Surface((CHUNK_PIXELS, CHUNK_PIXELS), pygame.SRCALPHA)
        self._pattern(overlay, key)
        mask = pygame.Surface((CHUNK_PIXELS, CHUNK_PIXELS), pygame.SRCALPHA);mask.fill((0,0,0,0))
        painter(mask)
        overlay.blit(mask, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
        target.blit(overlay, (0,0))

    def _feature_intersects(self, points, chunk_rect, padding=0):
        if not points:return False
        xs, ys = zip(*points)
        left,top = min(xs)*TILE_SIZE-padding,min(ys)*TILE_SIZE-padding
        right,bottom = max(xs)*TILE_SIZE+padding,max(ys)*TILE_SIZE+padding
        return (left < chunk_rect.right and right >= chunk_rect.left
                and top < chunk_rect.bottom and bottom >= chunk_rect.top)

    def _render_chunk(self, cx, cy):
        key = (cx, cy);cached = self._render_cache.get(key)
        if cached is not None:return cached
        surface = pygame.Surface((CHUNK_PIXELS, CHUNK_PIXELS))
        if self._chunk_metadata(cx, cy) is None:
            surface.fill('#283d38');return surface
        terrain = self.region.get('terrain', {})
        ox, oy = cx*CHUNK_PIXELS, cy*CHUNK_PIXELS
        chunk_rect = pygame.Rect(ox, oy, CHUNK_PIXELS, CHUNK_PIXELS)
        if self.environment is not None:
            self.environment.ground(surface,cx,cy)
            self.environment.roads(surface,cx,cy)
        else:
            self._pattern(surface, 'grass')
            for category, key in (('forests','forest_floor'), ('fields','field'), ('hills','grass'), ('scorched','scorched')):
                for feature in terrain.get(category, []):
                    if not self._feature_intersects(feature['polygon'], chunk_rect):continue
                    polygon = [(round(x*TILE_SIZE-ox), round(y*TILE_SIZE-oy)) for x, y in feature['polygon']]
                    self._paint_shape(surface, key, lambda mask, polygon=polygon: pygame.draw.polygon(mask, 'white', polygon))
            for road in self.region.get('roads', []):
                if not self._feature_intersects(road['points'], chunk_rect, road.get('width',3)*TILE_SIZE/2+10):continue
                points = self._local_path(road, cx, cy);width = road.get('width', 3)*TILE_SIZE
                self._draw_path(surface, '#8e9568', points, width+10)
                self._paint_shape(surface, road.get('surface','dirt'), lambda mask, p=points, w=width: self._draw_path(mask, 'white', p, w))
        if not self._bridge_repaired():
            # The strike destroyed road approaches as well as the span. Let the
            # authored scorched polygons interrupt the stone road on both banks.
            for feature in terrain.get('scorched',[]):
                if self.environment is not None:
                    self.environment.polygon(surface,feature,'scorched',cx,cy,4)
                    continue
                if not self._feature_intersects(feature['polygon'],chunk_rect):continue
                polygon = [(round(x*TILE_SIZE-ox),round(y*TILE_SIZE-oy)) for x,y in feature['polygon']]
                self._paint_shape(surface,'scorched',lambda mask,p=polygon:pygame.draw.polygon(mask,'white',p))
        for river in terrain.get('rivers', []):
            fringe = 40 if self.environment is not None else 24
            if not self._feature_intersects(river['points'], chunk_rect, river.get('width',8)*TILE_SIZE/2+fringe):continue
            points = self._local_path(river, cx, cy);width = river.get('width',8)*TILE_SIZE
            if self.environment is not None:self.environment.bank(surface,river,cx,cy)
            else:self._paint_shape(surface, 'bank', lambda mask, p=points, w=width: self._draw_path(mask, 'white', p, w+24))
            self._paint_shape(surface, 'water', lambda mask, p=points, w=width: self._draw_path(mask, 'white', p, w))
        bridge = self.region.get('bridge')
        if bridge and self._bridge_repaired():
            rect = self._tile_rect(bridge.get('deck_rect_tiles',bridge['damage_rect_tiles'])).move(-ox,-oy)
            if chunk_rect.colliderect(self._tile_rect(bridge.get('deck_rect_tiles',bridge['damage_rect_tiles']))):
                pygame.draw.rect(surface, '#756c52', rect.inflate(0,8))
                pygame.draw.rect(surface, '#b2a081', rect)
                for y in range(rect.top+4, rect.bottom, 8):pygame.draw.line(surface, '#8d7c64', (rect.left,y), (rect.right,y))
        for wall in self.region.get('walls', []):
            for left, right in self._wall_segments(wall):
                rect = self._tile_rect((left,wall['y']-.5,right-left,1)).move(-ox,-oy)
                pygame.draw.rect(surface, '#727c6b', rect)
        return self._render_cache.put((cx,cy), surface)

    def _static_props(self, viewport):
        """Yield visible props once, including canopies owned by adjacent chunks."""
        expanded = viewport.inflate(320, 260)
        for cx in range(expanded.left//CHUNK_PIXELS, (expanded.right-1)//CHUNK_PIXELS+1):
            for cy in range(expanded.top//CHUNK_PIXELS, (expanded.bottom-1)//CHUNK_PIXELS+1):
                metadata = self._chunk_metadata(cx, cy)
                if metadata:
                    yield from metadata['props']
        town = self.region.get('town')
        if town:yield {'key':'eldenmere', 'position': self._tile_point(town['tile_position'])}
        bridge = self.region.get('bridge')
        if bridge and not self._bridge_repaired():yield {'key':'broken_bridge', 'position':self._tile_point(bridge['tile_position'])}
        yield from self._bridge_debris()
        for landmark in self.region.get('landmarks', []):
            if landmark.get('prop'):yield {'key':landmark['prop'], 'position':self._tile_point(landmark['tile_position'])}
        for wall in self.region.get('walls', []):
            if abs(wall['y']*TILE_SIZE-viewport.centery) > viewport.height/2+90:continue
            for left, right in self._wall_segments(wall):
                start = max(left, math.floor(expanded.left/TILE_SIZE/2)*2)
                end = min(right, expanded.right/TILE_SIZE)
                for x in range(math.ceil(start/2)*2, math.ceil(end/2)*2, 2):
                    if x+1 > right:continue
                    key = 'wall_segment'
                    if self.environment is not None:
                        seed = _stable_hash(x,round(wall['y']),53)
                        preferred = 'wall_segment_moss' if seed%5 == 0 else 'wall_segment_worn' if seed%7 == 0 else key
                        if preferred in self._art.get('props',{}):key = preferred
                    yield {'key':key, 'position':self._tile_point((x+1, wall['y']+.5))}
        for gate in self.gates:
            if not self._gate_open(gate):yield {'key':'checkpoint', 'position':gate['position']}

    def _draw_water(self, target, camera, elapsed_ms):
        # Shared, deterministic little highlights, rather than animated grounds.
        phase = int(elapsed_ms//450)%3
        for x in range(math.floor(camera[0]/48)*48, camera[0]+target.get_width()+48, 48):
            for y in range(math.floor(camera[1]/48)*48, camera[1]+target.get_height()+48, 48):
                seed = _stable_hash(x//48, y//48)
                if seed%3 != phase:continue
                point = (x/TILE_SIZE, y/TILE_SIZE)
                if any(_distance_to_path(point, r['points']) < r.get('width',8)/2-.75 for r in self.region.get('terrain', {}).get('rivers', [])):
                    bridge = self.region.get('bridge')
                    if bridge and self._bridge_repaired() and self._tile_rect(bridge.get('deck_rect_tiles',bridge['damage_rect_tiles'])).collidepoint(x,y):continue
                    key = f'water_glint_{1+phase%2}'
                    if key in self._art.get('tiles',{}):
                        target.blit(self._tile_image(key),(x-camera[0]-12,y-camera[1]-12))
                    else:
                        pygame.draw.line(target, '#82aaa2', (x-camera[0], y-camera[1]), (x-camera[0]+5+seed%6, y-camera[1]))

    def draw(self, target, camera, player, elapsed_ms, include_ui=True):
        target.fill('#283d38')
        camera = tuple(round(v) for v in camera)
        viewport = pygame.Rect(camera, target.get_size())
        for cx in range(viewport.left//CHUNK_PIXELS, (viewport.right-1)//CHUNK_PIXELS+1):
            for cy in range(viewport.top//CHUNK_PIXELS, (viewport.bottom-1)//CHUNK_PIXELS+1):
                target.blit(self._render_chunk(cx,cy), (cx*CHUNK_PIXELS-camera[0],cy*CHUNK_PIXELS-camera[1]))
        self._draw_water(target,camera,elapsed_ms)
        ordered = []
        for prop in self._static_props(viewport):
            key,position = (self.environment.prop_frame(prop,elapsed_ms) if self.environment is not None
                            else (prop['key'],prop['position']))
            surface, anchor = self._prop_image(key)
            if surface is None:continue
            x,y = position;rect = surface.get_rect(topleft=(round(x)-anchor[0],round(y)-anchor[1]))
            if rect.colliderect(viewport):ordered.append((prop['position'][1]+prop.get('sort_offset',0),1,surface,rect.topleft))
        for actor, priority in [(npc,2) for npc in self.npcs]+[(player,3)]:
            if not getattr(actor,'story_visible',True):continue
            position = getattr(actor,'story_position',None) or actor.position
            anchor = getattr(actor,'story_draw_anchor',None) or (self.data['player_draw_anchor'] if actor is player else actor.draw_anchor)
            surface = getattr(actor,'story_sprite',None)
            if surface is None:surface = actor.sprite() if actor is player else actor.sprite(elapsed_ms)
            rect = surface.get_rect(topleft=(round(position[0])-anchor[0],round(position[1])-anchor[1]))
            if rect.colliderect(viewport):ordered.append((getattr(actor,'story_sort_y',None) or position[1]+6,priority,surface,rect.topleft))
        for _,_,surface,position in sorted(ordered,key=lambda record:(record[0],record[1])):
            target.blit(surface,(position[0]-camera[0],position[1]-camera[1]))
        # Spread the one-chunk lookahead ring over frames. Ordinary walking
        # reaches an already prepared neighbour without loading the region.
        candidates = [(cx,cy)
                      for cx in range(viewport.left//CHUNK_PIXELS-1, (viewport.right-1)//CHUNK_PIXELS+2)
                      for cy in range(viewport.top//CHUNK_PIXELS-1, (viewport.bottom-1)//CHUNK_PIXELS+2)
                      if (cx,cy) not in self._render_cache.items and self._has_chunk(cx,cy)]
        if candidates:
            center = (viewport.centerx/CHUNK_PIXELS,viewport.centery/CHUNK_PIXELS)
            cx,cy = min(candidates,key=lambda coord:math.dist((coord[0]+.5,coord[1]+.5),center))
            self._render_chunk(cx,cy)

    def location(self, position):
        if self.data['landmarks']:
            nearest = min(self.data['landmarks'],key=lambda record:math.dist(position,record['position']))
            if math.dist(position,nearest['position'])<180:return nearest['name']
        return self.data['name']
