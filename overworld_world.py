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

from dense_art import draw_actor
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
    """A fixed post with authored views and a single restrained greeting.

    Turning changes the whole pose, including the shield's physical side. It
    never rotates an arm or mirrors asymmetric equipment at runtime.
    """
    def __init__(self, world, gate, position=None, index=0):
        self.data = {'id': f'road_guard:{gate["id"]}:{index}', 'name': 'Road guard'}
        self.position = pygame.Vector2(position or gate['guard_position'])
        self.scene_id = world.data['id']
        self.probe_size = (12, 8)
        self.watch_facing = 'front' if self.position.y < 0 else 'back'
        self.facing = self.watch_facing
        self.moving = False
        self._conversation_started_ms = None
        if not hasattr(world, '_road_guard_art'):
            folder = ROOT/'assets/characters/road_guards'
            manifest = json.loads((folder/'animation.json').read_text())
            frames = {name: pygame.image.load(str(folder/name)).convert_alpha()
                      for name in set(manifest['poses'].values())}
            if any(image.get_size() != tuple(manifest['canvas']) for image in frames.values()):
                raise ValueError('Road guard poses must share their authored canvas')
            for clip in manifest['clips'].values():
                if not clip['frames'] or any(
                        frame['file'] not in frames or type(frame['duration_ms']) not in (int,float)
                        or not math.isfinite(frame['duration_ms']) or frame['duration_ms'] <= 0
                        for frame in clip['frames']):
                    raise ValueError('Invalid road guard animation clip')
            world._road_guard_art = (manifest, frames)
        self._art, self._frames = world._road_guard_art
        self.draw_anchor = tuple(self._art['draw_anchor'])

    @property
    def blocker(self):
        return pygame.Rect(round(self.position.x)-6, round(self.position.y)-4, 12, 8)

    def begin_conversation(self, facing, elapsed_ms):
        if facing not in ('front', 'back', 'left', 'right'):
            raise ValueError('Unknown guard conversation direction')
        self.facing = facing
        self._conversation_started_ms = elapsed_ms

    def end_conversation(self):
        self.facing = self.watch_facing
        self._conversation_started_ms = None

    def sprite(self, elapsed_ms):
        key = 'idle_'+self.facing
        clock = max(0, elapsed_ms)
        if self._conversation_started_ms is not None:
            greeting = self._art['clips']['greet_'+self.facing]
            since = max(0, elapsed_ms-self._conversation_started_ms)
            if since < sum(frame['duration_ms'] for frame in greeting['frames']):
                key = 'greet_'+self.facing;clock = since
        clip = self._art['clips'][key]
        total = sum(frame['duration_ms'] for frame in clip['frames'])
        clock = clock % total if clip['loop'] else min(clock, total-1)
        for frame in clip['frames']:
            if clock < frame['duration_ms']:return self._frames[frame['file']]
            clock -= frame['duration_ms']
        return self._frames[clip['frames'][-1]['file']]


class OverworldWorld:
    """One world identity across every sparse chunk in the regional manifest."""
    is_overworld = True

    def __init__(self, path=REGION_FILE, progress_flags=(), *, bridge_condition=None,
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
        self._bridge_condition = self._resolve_bridge_condition(bridge_condition) if bridge_condition is not None else None
        self._revision = 0
        self._whitelist = (set(map(tuple, self.region['chunk_whitelist']))
                           if 'chunk_whitelist' in self.region else None)
        self.blocked = _BlockedView(self)
        self.doors = [];self.routine_props = [];self.work_fittings = [];self.foreground = []
        self.entities = []
        self._art = {};self._tiles = {};self._props = {}
        self._load_art()
        self._bridge_art = self._load_bridge_layers()
        self._validate_bridge_width()
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
        from grain_farm import GrainFarm
        self.grain_farm = GrainFarm(self)
        self.npcs.extend(self.grain_farm.actors)
        from bridge_crew import BridgeCrew
        self.bridge_crew = BridgeCrew(self)
        self.npcs.extend(self.bridge_crew.actors)
        from garden_orchard import GardenOrchard
        self.garden_orchard = GardenOrchard(self)
        self.npcs.extend(self.garden_orchard.actors)
        from purposeful_wildlife import PurposefulWildlife, REPLACED_PROP_IDS
        self._wildlife_prop_ids = REPLACED_PROP_IDS
        self.wildlife = PurposefulWildlife(self)
        from checkpoint_charm import CheckpointCharm
        self.checkpoint_charm = CheckpointCharm(self)
        from regional_participation import RegionalParticipation
        self.participation = RegionalParticipation(self)

    @staticmethod
    def _tile_point(point):return tuple(value*TILE_SIZE for value in point)

    @staticmethod
    def _tile_rect(rect):return pygame.Rect(*(round(value*TILE_SIZE) for value in rect))

    @property
    def progress_flags(self):return self._flags

    def _resolve_bridge_condition(self, value):
        from bridge_condition import resolve_condition
        return resolve_condition(value, flags=self._flags,
                                 repair_flag=self.region.get('bridge', {}).get('repair_flag'))

    @property
    def bridge_condition(self):
        return self._resolve_bridge_condition(self._bridge_condition)

    @property
    def cache_stats(self):
        return {'render_bytes': self._render_cache.weight,
                'render_chunks': len(self._render_cache.items),
                'collision_chunks': len(self._collision_cache.items),
                'metadata_chunks': len(self._metadata_cache.items)}

    def set_progress(self, flags, *, bridge_condition=None):
        flags = frozenset(flags)
        previous = self.bridge_condition
        explicit = (self._resolve_bridge_condition(bridge_condition)
                    if bridge_condition is not None else self._bridge_condition)
        relevant = {gate.get('clearance_flag') for gate in self.gates}
        changed = self._flags.intersection(relevant) != flags.intersection(relevant)
        self._flags = flags
        self._bridge_condition = explicit
        changed = changed or previous != self.bridge_condition
        if not changed:return
        self._revision += 1
        # Geometry is derived from durable facts, never from cache contents.
        self._collision_cache.clear();self._render_cache.clear()

    def _load_art(self):
        candidate = self.region.get('art', self.region.get('art_manifest'))
        path = ROOT/candidate if isinstance(candidate, str) else ART_FILE
        self.art_available = path.exists()
        if self.art_available:self._art = json.loads(path.read_text(encoding='utf-8'))
        for field in ('detail_art_manifest','composition_art_manifest','sanctuary_art_manifest'):
            detail = self.region.get(field)
            if detail and (ROOT/detail).exists():
                additional = json.loads((ROOT/detail).read_text(encoding='utf-8'))
                for group in ('tiles','props'):
                    self._art.setdefault(group,{}).update(additional.get(group,{}))

    def _load_bridge_layers(self):
        """Load registered ground and parapet layers; old fixture art is optional."""
        source = self.region.get('bridge', {}).get('layers_manifest')
        if not source:return None
        record = json.loads((ROOT/source).read_text(encoding='utf-8'))
        canvas, anchor = tuple(record['canvas']), tuple(record['anchor'])
        if record.get('version') != 1 or set(record['phases']) != {'intact','destroyed','restored'}:
            raise ValueError('Bridge layers require all three version-one phases')
        for phase in record['phases'].values():
            if set(phase) != {'deck','far','near'}:raise ValueError('Bridge phase requires deck and both parapets')
            for name, layer in phase.items():
                if tuple(layer['foot_anchor']) != anchor:raise ValueError('Bridge layers must share their anchor')
                image = pygame.image.load(str(ROOT/layer['image'])).convert_alpha()
                if image.get_size() != canvas:raise ValueError('Bridge layers must share their canvas')
                layer['surface'] = image
                if name != 'deck' and 'sort_offset' not in layer:
                    raise ValueError('Bridge parapets require a depth offset')
        return record

    def _validate_bridge_width(self):
        """A declared roadway width agrees in world geometry and exported art."""
        bridge = self.region.get('bridge',{})
        if 'deck_width_tiles' not in bridge:return
        width = bridge['deck_width_tiles']*TILE_SIZE
        deck = self._tile_rect(bridge['deck_rect_tiles'])
        if deck.height != width:
            raise ValueError('Bridge roadway width differs from its collision deck')
        center = bridge.get('deck_center_tile_y')
        if center is not None and deck.centery != round(center*TILE_SIZE):
            raise ValueError('Bridge roadway is not aligned with its approach')
        record = self._art.get('props',{}).get(bridge.get('broken_art_key'))
        if record and 'deck_clear_width_px' in record:
            if record['deck_clear_width_px'] != width:
                raise ValueError('Bridge artwork roadway differs from its collision width')
            if record['deck_bottom_px']-record['deck_top_px'] != width:
                raise ValueError('Bridge artwork deck bounds do not match its clear width')
            art_center = (record['deck_top_px']+record['deck_bottom_px'])/2
            offset = bridge['tile_position'][1]*TILE_SIZE-deck.centery
            if record['foot_anchor'][1] != art_center+offset:
                raise ValueError('Bridge artwork roadway is not aligned with the world deck')
        if self._bridge_art is not None:
            record = self._bridge_art
            if record['deck_bottom_px']-record['deck_top_px'] != width:
                raise ValueError('Bridge layer roadway differs from its collision width')
            top = bridge['tile_position'][1]*TILE_SIZE-record['anchor'][1]+record['deck_top_px']
            if top != deck.top:raise ValueError('Bridge layers are not aligned with the world roadway')

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

    def _bridge_passable(self):
        return self.bridge_condition.passable

    def _bridge_river(self):
        rivers = self.region.get('terrain', {}).get('rivers', [])
        if not rivers:return None
        identifier = self.region.get('far_bank', {}).get('western_river_id', 'western_boundary_river')
        return next((river for river in rivers if river.get('id') == identifier),
                    min(rivers, key=lambda river: _distance_to_path(
                        self.region.get('bridge', {}).get('tile_position', (0,0)), river['points'])))

    def bridge_bank(self, position):
        """Classify a landing against the nearby bend, rather than a fixed meridian."""
        river = self._bridge_river()
        point = (position[0]/TILE_SIZE, position[1]/TILE_SIZE)
        if river is None:
            nearest_x = self.region.get('bridge', {}).get('tile_position', (0,0))[0]
        else:
            nearest = (math.inf, river['points'][0][0])
            for a,b in zip(river['points'], river['points'][1:]):
                dx,dy = b[0]-a[0],b[1]-a[1];length2 = dx*dx+dy*dy
                t = 0 if not length2 else max(0,min(1,((point[0]-a[0])*dx+(point[1]-a[1])*dy)/length2))
                x,y = a[0]+t*dx,a[1]+t*dy
                candidate = ((point[0]-x)**2+(point[1]-y)**2,x)
                if candidate[0] < nearest[0]:nearest = candidate
            nearest_x = nearest[1]
        return 'west' if point[0] < nearest_x else 'east'

    def _bridge_walkable_rects(self):
        bridge = self.region.get('bridge')
        if not bridge:return []
        rects = ([bridge.get('deck_rect_tiles', bridge['damage_rect_tiles'])]
                 if self._bridge_passable() else bridge.get('destroyed_walkable_rect_tiles', []))
        return [self._tile_rect(rect) for rect in rects]

    def _far_bank_collision(self, surface, cx, cy):
        boundary = self.region.get('far_bank')
        river = self._bridge_river()
        if not boundary or not river:return
        ox,oy = cx*CHUNK_PIXELS,cy*CHUNK_PIXELS
        # Only territory west of the boundary river is constrained. The central
        # vale and its north/south checkpoints retain their independent geometry.
        points = sorted(river['points'], key=lambda point:point[1])
        left = self.bounds.left/TILE_SIZE-1
        western = [(left, self.bounds.top/TILE_SIZE-1), (points[0][0], self.bounds.top/TILE_SIZE-1)]
        western += points
        western += [(points[-1][0], self.bounds.bottom/TILE_SIZE+1), (left,self.bounds.bottom/TILE_SIZE+1)]
        local = lambda polygon:[(round(x*TILE_SIZE-ox),round(y*TILE_SIZE-oy)) for x,y in polygon]
        mask = pygame.Surface((CHUNK_PIXELS,CHUNK_PIXELS));mask.fill('black')
        pygame.draw.polygon(mask,'white',local(western))
        pygame.draw.polygon(mask,'black',local(boundary['playable_polygon']))
        surface.blit(mask,(0,0),special_flags=pygame.BLEND_RGB_MAX)
        for segment in boundary.get('boundary_segments', []):
            self._draw_path(surface,'white',local(segment['points']),segment.get('width_tiles',1)*TILE_SIZE)

    def _far_bank_dressing(self):
        """Stable irregular shelf dressing, displaced toward the unwalkable side."""
        boundary = self.region.get('far_bank', {})
        polygon = boundary.get('playable_polygon', [])
        for index,segment in enumerate(boundary.get('boundary_segments', [])):
            count = 0;remaining = 0
            for a,b in zip(segment['points'],segment['points'][1:]):
                length = math.dist(a,b)*TILE_SIZE
                if not length:continue
                tx,ty = (b[0]-a[0])*TILE_SIZE/length,(b[1]-a[1])*TILE_SIZE/length
                nx,ny = -ty,tx
                while remaining <= length:
                    seed = _stable_hash(index,count,83)
                    x,y = a[0]*TILE_SIZE+tx*remaining,a[1]*TILE_SIZE+ty*remaining
                    outward = -1 if _point_in_polygon((x/TILE_SIZE+nx*.75,y/TILE_SIZE+ny*.75),polygon) else 1
                    normal = (nx*outward,ny*outward)
                    width = segment.get('width_tiles',1)*TILE_SIZE
                    yield (x,y),normal,width/2-3+seed%6,seed
                    remaining += 12+seed%9
                    count += 1
                remaining -= length

    def _scorched_feature_visible(self, feature):
        bridge_scorch = {'broken_bridge_east_bank', 'broken_bridge_west_bank'}
        return feature.get('id') not in bridge_scorch or self.bridge_condition.phase != 'intact'

    def _bridge_debris(self):
        bridge = self.region.get('bridge')
        if not bridge or not self.bridge_condition.destroyed:return []
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
        self._far_bank_collision(surface,cx,cy)
        bridge = self.region.get('bridge')
        if bridge:
            if not self._bridge_passable():
                rect = self._tile_rect(bridge['damage_rect_tiles']).move(-origin[0], -origin[1])
                pygame.draw.rect(surface, 'white', rect)
            for rect in self._bridge_walkable_rects():
                pygame.draw.rect(surface,'black',rect.move(-origin[0],-origin[1]))
            if self._bridge_art is not None and self.bridge_condition.destroyed:
                # The authored rectangles bound the surviving supports; their
                # broken tips are jagged. Transparent floor pixels remain unsafe.
                record = self._bridge_art
                layer = record['phases']['destroyed']['deck']
                holes = pygame.mask.from_surface(layer['surface']).to_surface(
                    setcolor='black',unsetcolor='white')
                area = pygame.Rect(0,record['deck_top_px'],record['canvas'][0],
                                   record['deck_bottom_px']-record['deck_top_px'])
                x,y = self._tile_point(bridge['tile_position']);anchor = layer['foot_anchor']
                surface.blit(holes,(round(x)-anchor[0]-origin[0],round(y)-anchor[1]+area.y-origin[1]),
                             area,special_flags=pygame.BLEND_RGB_MAX)
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
        crew = getattr(self, 'bridge_crew', None)
        if crew and any(block.colliderect(rect) for block in crew.ground_blockers(ignore_npc)):return False
        farm = getattr(self, 'grain_farm', None)
        if farm and any(block.colliderect(rect) for block in farm.ground_blockers(ignore_npc)):return False
        garden = getattr(self, 'garden_orchard', None)
        if garden and any(block.colliderect(rect) for block in garden.ground_blockers(ignore_npc)):return False
        wildlife = getattr(self, 'wildlife', None)
        if wildlife and any(block.colliderect(rect) for block in wildlife.ground_blockers(ignore_npc)):return False
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
                    if category == 'scorched' and not self._scorched_feature_visible(feature):continue
                    if not self._feature_intersects(feature['polygon'], chunk_rect):continue
                    polygon = [(round(x*TILE_SIZE-ox), round(y*TILE_SIZE-oy)) for x, y in feature['polygon']]
                    self._paint_shape(surface, key, lambda mask, polygon=polygon: pygame.draw.polygon(mask, 'white', polygon))
            for road in self.region.get('roads', []):
                if not self._feature_intersects(road['points'], chunk_rect, road.get('width',3)*TILE_SIZE/2+10):continue
                points = self._local_path(road, cx, cy);width = road.get('width', 3)*TILE_SIZE
                self._draw_path(surface, '#8e9568', points, width+10)
                self._paint_shape(surface, road.get('surface','dirt'), lambda mask, p=points, w=width: self._draw_path(mask, 'white', p, w))
        # Only the bridge's named damage features depend on its condition.
        # Unrelated scorched terrain remains visible in every bridge phase.
        for feature in terrain.get('scorched',[]):
            if not self._scorched_feature_visible(feature):continue
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
        if self.region.get('far_bank', {}).get('boundary_segments'):
            def shelf_gravel(mask):
                for (x,y),(nx,ny),radius,seed in self._far_bank_dressing():
                    center = (round(x+nx*(seed%4)-ox),round(y+ny*(seed%4)-oy))
                    pygame.draw.circle(mask,'white',center,round(radius))
            self._paint_shape(surface,'gravel' if 'gravel' in self._art.get('tiles',{}) else 'dirt',shelf_gravel)
        bridge = self.region.get('bridge')
        if self._bridge_art is not None:
            layer = self._bridge_art['phases'][self.bridge_condition.phase]['deck']
            x,y = self._tile_point(bridge['tile_position']);anchor = layer['foot_anchor']
            surface.blit(layer['surface'],(round(x)-anchor[0]-ox,round(y)-anchor[1]-oy))
        elif bridge and self._bridge_passable():
            rect = self._tile_rect(bridge.get('deck_rect_tiles',bridge['damage_rect_tiles'])).move(-ox,-oy)
            if chunk_rect.colliderect(self._tile_rect(bridge.get('deck_rect_tiles',bridge['damage_rect_tiles']))):
                pygame.draw.rect(surface, '#77786c', rect.inflate(0,8))
                key = 'stone_road_worn' if 'stone_road_worn' in self._art.get('tiles',{}) else 'stone_road'
                self._paint_shape(surface,key,lambda mask,r=rect:pygame.draw.rect(mask,'white',r))
                pygame.draw.line(surface,'#b2b6a4',(rect.left,rect.top-2),(rect.right,rect.top-2),2)
                pygame.draw.line(surface,'#606c5b',(rect.left,rect.bottom+2),(rect.right,rect.bottom+2),2)
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
                    # The regional controller owns these identities once. Chunk
                    # reactivation must never resurrect the decorative copies.
                    yield from (prop for prop in metadata['props']
                                if prop.get('id') not in self._wildlife_prop_ids)
        town = self.region.get('town')
        if town:yield {'key':'eldenmere', 'position': self._tile_point(town['tile_position'])}
        bridge = self.region.get('bridge')
        if bridge and self.bridge_condition.destroyed and self._bridge_art is None:
            key = bridge.get('broken_art_key','broken_bridge')
            if key not in self._art.get('props',{}):key = 'broken_bridge'
            yield {'key':key,'position':self._tile_point(bridge['tile_position'])}
        yield from self._bridge_debris()
        for (x,y),(nx,ny),_,seed in self._far_bank_dressing():
            preferred = 'rock_outcrop' if seed%3 == 0 else 'river_rocks' if seed%2 else 'rock'
            key = preferred if preferred in self._art.get('props',{}) else 'rock'
            # Larger silhouettes sit farther out. Their inner edge stays on
            # the solid shelf rather than overhanging the usable road.
            distance = 26 if key == 'rock_outcrop' else 14+seed%5
            tangent_jitter = seed%11-5
            position = (x+nx*distance-ny*tangent_jitter,y+ny*distance+nx*tangent_jitter)
            if expanded.collidepoint(position):yield {'key':key,'position':position}
            if key == 'rock_outcrop':
                position = (x+nx*13+ny*17,y+ny*13-nx*17)
                if expanded.collidepoint(position):
                    key = 'river_rocks' if 'river_rocks' in self._art.get('props',{}) else 'rock'
                    yield {'key':key,'position':position}
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
                    if any(rect.collidepoint(x,y) for rect in self._bridge_walkable_rects()):continue
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
        if self._bridge_art is not None:
            x,y = self._tile_point(self.region['bridge']['tile_position'])
            for name in ('far','near'):
                layer = self._bridge_art['phases'][self.bridge_condition.phase][name]
                anchor = layer['foot_anchor'];image = layer['surface']
                rect = image.get_rect(topleft=(round(x)-anchor[0],round(y)-anchor[1]))
                if rect.colliderect(viewport):ordered.append((y+layer['sort_offset'],1,image,rect.topleft))
        for prop in self._static_props(viewport):
            key,position = (self.environment.prop_frame(prop,elapsed_ms) if self.environment is not None
                            else (prop['key'],prop['position']))
            surface, anchor = self._prop_image(key)
            if surface is None:continue
            x,y = position;rect = surface.get_rect(topleft=(round(x)-anchor[0],round(y)-anchor[1]))
            if rect.colliderect(viewport):ordered.append((prop['position'][1]+prop.get('sort_offset',0),1,surface,rect.topleft))
        ordered.extend(self.bridge_crew.props())
        ordered.extend(self.garden_orchard.props())
        ordered.extend(self.grain_farm.props())
        ordered.extend(self.grain_farm.cover_props())
        ordered.extend(self.wildlife.props())
        for actor, priority in [(npc,2) for npc in self.npcs]+[(player,3)]:
            if not getattr(actor,'story_visible',True):continue
            position = getattr(actor,'story_position',None) or actor.position
            anchor = getattr(actor,'story_draw_anchor',None) or (self.data['player_draw_anchor'] if actor is player else actor.draw_anchor)
            surface = getattr(actor,'story_sprite',None)
            if surface is None:surface = actor.sprite() if actor is player else actor.sprite(elapsed_ms)
            rect = surface.get_rect(topleft=(round(position[0])-anchor[0],round(position[1])-anchor[1]))
            if rect.colliderect(viewport):ordered.append((getattr(actor,'story_sort_y',None) or position[1]+6,priority,(actor,surface,anchor,position),None))
        for _,_,surface,position in sorted(ordered,key=lambda record:(record[0],record[1])):
            if position is None:
                actor,image,anchor,world_position=surface
                draw_actor(target,actor,image,(round(world_position[0])-anchor[0]-camera[0],round(world_position[1])-anchor[1]-camera[1]),elapsed_ms)
            else:target.blit(surface,(position[0]-camera[0],position[1]-camera[1]))
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
