"""Distance-based encounters for the single continuous Sanctuary cave.

This owner selects durable encounter facts. It never moves an actor, opens a
battle, settles resources or writes a journey. The game supplies actual player
travel after collision resolution and pauses calls when exploration is locked.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
from pathlib import Path
import random
import re

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT/'assets/combat/cave_encounters.json'
MAP_PATH = ROOT/'assets/maps/sanctuary_cave/map.json'
SCENE_ID = 'sanctuary_cave'
SAVE_KEY = 'cave_random_encounters'
AREAS = ('outer', 'middle', 'deep')
# Pending encounters retain their committed levels across the Lucan rebalance.
# Only validation uses these ranges; new selections use the current area table.
LEGACY_LEVELS = {
    'outer': {'cave_bat': (2, 2), 'lithrusk': (2, 2)},
    'middle': {'cave_bat': (2, 3), 'lithrusk': (2, 3), 'veylume': (3, 3)},
    'deep': {'cave_bat': (3, 3), 'lithrusk': (3, 3), 'veylume': (3, 4)},
}
BATTLEFIELDS = frozenset(('cave_outer', 'cave_grotto', 'cave_hollow', 'cave_depths'))
UINT32 = 2**32-1
STATE_FIELDS = frozenset(('version', 'identity', 'rng_state', 'sequence',
                          'threshold', 'remaining', 'was_safe', 'pending'))
TICKET_FIELDS = frozenset(('version', 'receipt', 'area', 'location', 'battlefield',
                           'formation', 'members', 'combat_seed', 'position'))


def _integer(value, low=0, high=UINT32):
    return type(value) is int and low <= value <= high


def _number(value, low=0., high=1e7):
    return type(value) in (int, float) and low <= value <= high and math.isfinite(value)


def _point(value):
    try:
        values = list(value)
    except TypeError:
        return None
    return tuple(values) if len(values) == 2 and all(_number(v, -1e7) for v in values) else None


def _inside(point, polygon):
    """Closed polygon membership; boundary points are protected in safe areas."""
    x, y = point
    inside = False
    for a, b in zip(polygon, polygon[1:]+polygon[:1]):
        ax, ay = a;bx, by = b
        cross = (x-ax)*(by-ay)-(y-ay)*(bx-ax)
        if abs(cross) <= 1e-7 and min(ax,bx)-1e-8 <= x <= max(ax,bx)+1e-8 and min(ay,by)-1e-8 <= y <= max(ay,by)+1e-8:
            return True
        if (ay > y) != (by > y) and x < (bx-ax)*(y-ay)/(by-ay)+ax:
            inside = not inside
    return inside


def _distance(point, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    span = dx*dx+dy*dy
    fraction = 0. if not span else max(0., min(1., ((point[0]-a[0])*dx+(point[1]-a[1])*dy)/span))
    return math.hypot(point[0]-a[0]-dx*fraction, point[1]-a[1]-dy*fraction)


def load_encounters(data=None, map_data=None, bestiary_data=None):
    """Validate the roster, probabilities and explicit authored route coverage."""
    if data is None:data = json.loads(CONFIG_PATH.read_text())
    if map_data is None:map_data = json.loads(MAP_PATH.read_text())
    if bestiary_data is None:
        from bestiary import load_bestiary
        bestiary_data = load_bestiary()
    expected = {'version','scene','tile_size','distance_tiles','formations','areas','rooms','safe_polygons','routes'}
    if (not isinstance(data, dict) or set(data) != expected or data['version'] != 1
            or type(data['version']) is not int or data['scene'] != SCENE_ID
            or map_data.get('id') != SCENE_ID or data['tile_size'] != map_data.get('tile_size')
            or not _integer(data['tile_size'],1,128)):
        raise ValueError('Invalid cave encounter configuration')
    distances = data['distance_tiles']
    if (not isinstance(distances, dict) or set(distances) != {'minimum','mode','maximum','safe_exit'}
            or any(not _integer(v,1,10000) for v in distances.values())
            or not distances['minimum'] <= distances['mode'] <= distances['maximum']
            or distances['safe_exit'] >= distances['minimum']):
        raise ValueError('Invalid cave encounter spacing')
    forms = data['formations']
    catalog = bestiary_data['enemies']
    if not isinstance(forms, dict) or not forms:
        raise ValueError('Invalid cave formations')
    for name, members in forms.items():
        if (not isinstance(name, str) or re.fullmatch(r'[a-z][a-z0-9_]{0,63}',name) is None
                or not isinstance(members,list) or not 1 <= len(members) <= 4
                or any(not isinstance(e,str) or e not in ('cave_bat','lithrusk','veylume')
                       or e not in catalog for e in members)
                or members.count('lithrusk') > 1 or members.count('veylume') > 1):
            raise ValueError('Invalid cave formation')
    if not isinstance(data['areas'],dict) or set(data['areas']) != set(AREAS):
        raise ValueError('Invalid cave encounter areas')
    for name, area in data['areas'].items():
        if (not isinstance(area,dict) or set(area) != {'levels','weights'}
                or not isinstance(area['weights'],dict) or set(area['weights']) != set(forms)
                or any(not _integer(w,0,100) for w in area['weights'].values())
                or sum(area['weights'].values()) != 100 or not isinstance(area['levels'],dict)):
            raise ValueError('Invalid cave formation weights')
        species = {e for f,w in area['weights'].items() if w for e in forms[f]}
        if set(area['levels']) != species:raise ValueError('Cave levels do not match its roster')
        for species_id, limits in area['levels'].items():
            authored = catalog[species_id]['level_range']
            if (not isinstance(limits,list) or len(limits) != 2
                    or not _integer(limits[0],authored['min'],authored['max'])
                    or not _integer(limits[1],limits[0],authored['max'])):
                raise ValueError('Cave level is outside the Bestiary range')
    rooms = {r['id']:r for r in map_data['cave']['rooms']}
    def region(value):
        return (isinstance(value,dict) and set(value) == {'area','battlefield'}
                and ((value['area'] is None and value['battlefield'] is None)
                     or (isinstance(value['area'],str) and value['area'] in AREAS
                         and isinstance(value['battlefield'],str) and value['battlefield'] in BATTLEFIELDS)))
    if (not isinstance(data['rooms'],dict) or set(data['rooms']) != set(rooms)
            or any(not region(value) for value in data['rooms'].values())):
        raise ValueError('Cave rooms need explicit encounter regions')
    if (not isinstance(data['safe_polygons'],dict) or not data['safe_polygons']
            or any(not isinstance(poly,list) or len(poly) < 3 or any(_point(p) is None for p in poly)
                   for poly in data['safe_polygons'].values())):
        raise ValueError('Invalid cave safe regions')
    routes = map_data['cave']['routes']
    if not isinstance(data['routes'],dict) or set(data['routes']) != set(routes):
        raise ValueError('Cave routes need explicit encounter regions')
    for name, route in data['routes'].items():
        if (not isinstance(route,dict) or set(route) != {'width','bands'}
                or not _integer(route['width'],24,512) or not isinstance(route['bands'],list)):
            raise ValueError('Invalid cave route region')
        covered = []
        for band in route['bands']:
            if (not isinstance(band,dict) or set(band) != {'first','last','area','battlefield'}
                    or not _integer(band['first'],0,len(routes[name])-2)
                    or not _integer(band['last'],band['first'],len(routes[name])-2)
                    or not region({k:band[k] for k in ('area','battlefield')})):
                raise ValueError('Invalid cave route band')
            covered.extend(range(band['first'],band['last']+1))
        if sorted(covered) != list(range(len(routes[name])-1)):
            raise ValueError('Cave route bands overlap or leave gaps')
    return deepcopy(data)


class CaveRandomEncounters:
    """One durable countdown shared by every room in the continuous cave."""

    def __init__(self, seed=None, *, data=None, map_data=None):
        self.map_data = deepcopy(map_data) if map_data is not None else json.loads(MAP_PATH.read_text())
        self.data = load_encounters(data, self.map_data)
        self.minimum_distance = self.data['distance_tiles']['minimum']*self.data['tile_size']
        self.maximum_distance = self.data['distance_tiles']['maximum']*self.data['tile_size']
        self.mode_distance = self.data['distance_tiles']['mode']*self.data['tile_size']
        self.safe_exit_distance = self.data['distance_tiles']['safe_exit']*self.data['tile_size']
        self._rooms = [(r,self.data['rooms'][r['id']]) for r in self.map_data['cave']['rooms']]
        self._segments = []
        self._polygons = list(self.data['safe_polygons'].values())+[r['polygon'] for r,_ in self._rooms]
        self._circles = []
        for name, route in self.data['routes'].items():
            points = self.map_data['cave']['routes'][name]
            radius = route['width']/2
            for band in route['bands']:
                for index in range(band['first'],band['last']+1):
                    a,b = points[index:index+2]
                    self._segments.append((name,index,a,b,radius,band))
                    dx,dy = b[0]-a[0],b[1]-a[1]
                    length = math.hypot(dx,dy)
                    nx,ny = -dy/length*radius,dx/length*radius
                    self._polygons.append([[a[0]+nx,a[1]+ny],[b[0]+nx,b[1]+ny],
                                           [b[0]-nx,b[1]-ny],[a[0]-nx,a[1]-ny]])
                    self._circles.extend(((a,radius),(b,radius)))
        self.reset(seed)

    def _draw(self):
        # A full-period 32-bit LCG keeps saves small and independent of Python's
        # implementation-specific random-state tuple. Use its full high bits.
        self._rng_state = (1664525*self._rng_state+1013904223)&UINT32
        return self._rng_state

    def _unit(self):return self._draw()/(UINT32+1)

    def _roll_distance(self):
        low,mode,high = self.minimum_distance,self.mode_distance,self.maximum_distance
        unit = self._unit()
        if high == low:return low
        if unit < (mode-low)/(high-low):return low+math.sqrt(unit*(high-low)*(mode-low))
        return high-math.sqrt((1-unit)*(high-low)*(high-mode))

    def reset(self, seed=None):
        if seed is None:seed = random.SystemRandom().getrandbits(32)
        if not _integer(seed):raise ValueError('Cave encounter seed must be a uint32')
        self._identity = self._rng_state = seed
        self._sequence = 0
        self._threshold = self._roll_distance()
        self._remaining = self._threshold
        self._was_safe = None
        self._pending = None

    @property
    def remaining_distance(self):return self._remaining

    @property
    def threshold_distance(self):return self._threshold

    @property
    def pending(self):return deepcopy(self._pending)

    @property
    def sequence(self):return self._sequence

    def region_at(self, position):
        """Resolve actual room polygons and authored corridor tubes, never walls."""
        point = _point(position)
        if point is None:return None
        x,y = point
        width,height = self.map_data['size_pixels']
        if not 0 <= x < width or not 0 <= y < height:return None
        for name,polygon in self.data['safe_polygons'].items():
            if _inside(point,polygon):return {'area':None,'battlefield':None,'location':name}
        for room,region in self._rooms:
            if region['area'] is None and _inside(point,room['polygon']):
                return dict(region,location=room['id'])
        matches = [(name,index,a,b,radius,region) for name,index,a,b,radius,region in self._segments
                   if _distance(point,a,b) <= radius+1e-8]
        for name,index,_,_,_,region in matches:
            if region['area'] is None:return {'area':None,'battlefield':None,'location':f'{name}:{index}'}
        rooms = [(room,region) for room,region in self._rooms if _inside(point,room['polygon'])]
        if rooms:
            room,region = min(rooms,key=lambda r:math.dist(point,r[0]['position']))
            return dict(region,location=room['id'])
        if matches:
            name,index,a,b,_,region = min(matches,key=lambda s:_distance(point,s[2],s[3]))
            return {'area':region['area'],'battlefield':region['battlefield'],'location':f'{name}:{index}'}
        return None

    # A short alias is convenient for authoring tools and tests.
    classify = region_at

    def _select(self, position, region, introductory=False):
        area = self.data['areas'][region['area']]
        if introductory:
            formation = 'bat_pair'
        else:
            pick = self._unit()*100
            formation = next(name for name,weight in area['weights'].items()
                             if (pick := pick-weight) < 0)
        members = []
        for species in self.data['formations'][formation]:
            low,high = (2,2) if introductory else area['levels'][species]
            level = low+int(self._unit()*(high-low+1))
            members.append({'enemy_id':species,'level':level})
        seed = self._draw()
        self._sequence += 1
        self._pending = {'version':1,'receipt':f'cave:{self._identity:08x}:{self._sequence}',
                         'area':region['area'],'location':region['location'],
                         'battlefield':region['battlefield'],'formation':formation,
                         'members':members,'combat_seed':seed,'position':list(position)}
        if introductory:self._pending['lesson'] = 'aqua_edge'
        self._remaining = 0.
        return self.pending

    def _spend(self, distance, position, region, introductory=False):
        if region is None or region['area'] is None:
            self._was_safe = True
            return None
        if self._was_safe:self._remaining = max(self._remaining,self.safe_exit_distance)
        self._was_safe = False
        if distance+1e-9 < self._remaining:
            self._remaining -= distance
            return None
        return self._select(position,region,introductory)

    def advance(self, distance, position, *, eligible=True, introductory=False):
        """Spend known travel within one region; ``travel`` also tracks crossings."""
        if type(eligible) is not bool or type(introductory) is not bool:raise ValueError('Invalid cave encounter eligibility')
        if not _number(distance):raise ValueError('Invalid cave travel distance')
        point = _point(position)
        if point is None:raise ValueError('Invalid cave travel position')
        if self._pending is not None:return self.pending
        if not eligible or not distance:return None
        return self._spend(distance,point,self.region_at(point),introductory)

    def _crossings(self, start, end):
        """Partition travel at real polygon/corridor boundaries, independent of FPS."""
        dx,dy = end[0]-start[0],end[1]-start[1]
        values = {0.,1.}
        for polygon in self._polygons:
            for a,b in zip(polygon,polygon[1:]+polygon[:1]):
                ex,ey = b[0]-a[0],b[1]-a[1]
                denominator = dx*ey-dy*ex
                if abs(denominator) < 1e-12:continue
                ax,ay = a[0]-start[0],a[1]-start[1]
                fraction = (ax*ey-ay*ex)/denominator
                along = (ax*dy-ay*dx)/denominator
                if 0 < fraction < 1 and -1e-10 <= along <= 1+1e-10:values.add(fraction)
        squared = dx*dx+dy*dy
        for center,radius in self._circles:
            ox,oy = start[0]-center[0],start[1]-center[1]
            linear = 2*(ox*dx+oy*dy)
            constant = ox*ox+oy*oy-radius*radius
            discriminant = linear*linear-4*squared*constant
            if discriminant < 0:continue
            root = math.sqrt(max(0.,discriminant))
            for fraction in ((-linear-root)/(2*squared),(-linear+root)/(2*squared)):
                if 0 < fraction < 1:values.add(fraction)
        return sorted(values)

    def travel(self, previous, current, *, eligible=True, scene_id=SCENE_ID,
               distance_scale=1., introductory=False, boss_defeated=False):
        """Count a collision-resolved path segment and interpolate its trigger feet.

        Callers must omit teleports and doorway placement. On a selected battle,
        the returned position marks the exact stopping point on the supplied
        segment, rather than the end of a long render frame. ``distance_scale``
        allocates a diagonal substep's Euclidean credit across its safe axis
        legs without interpolating through a blocked corner. After the durable boss
        defeat, halve that credit (including trigger interpolation) so expected
        encounters per travelled distance fall by 50%, without rerolling tickets.
        """
        start,end = _point(previous),_point(current)
        if (start is None or end is None or type(eligible) is not bool or type(introductory) is not bool
                or type(boss_defeated) is not bool
                or not _number(distance_scale, 1e-12, 1.)):
            raise ValueError('Invalid cave movement segment')
        distance_scale *= .5 if boss_defeated else 1.
        if self._pending is not None:return self.pending
        if not eligible or scene_id != SCENE_ID:return None
        distance = math.dist(start,end)
        if not distance:return None
        dx,dy = end[0]-start[0],end[1]-start[1]
        crossings = self._crossings(start,end)
        for low,high in zip(crossings,crossings[1:]):
            middle = (low+high)/2
            region = self.region_at((start[0]+dx*middle,start[1]+dy*middle))
            length = (high-low)*distance*distance_scale
            if region is None or region['area'] is None:
                self._was_safe = True
                continue
            if self._was_safe:self._remaining = max(self._remaining,self.safe_exit_distance)
            self._was_safe = False
            if self._remaining > length+1e-9:
                self._remaining -= length
                continue
            fraction = low+self._remaining/(distance*distance_scale)
            point = (start[0]+dx*fraction,start[1]+dy*fraction)
            # Safe boundaries are closed. Keep an exact-boundary trigger a
            # microscopic distance inside the traversed dangerous interval.
            actual = self.region_at(point)
            if actual is None or actual['area'] is None:
                # Use an absolute native-pixel epsilon, rather than a fraction
                # of a potentially tiny render-frame segment. Reclassify the
                # final point so the durable ticket agrees with closed safe
                # polygon edges even at exact threshold/boundary coincidences.
                toward = (start[0]+dx*middle-point[0],start[1]+dy*middle-point[1])
                span = math.hypot(*toward)
                for epsilon in (1e-5,1e-4,1e-3,span):
                    blend = min(1.,epsilon/span) if span else 1.
                    candidate = (point[0]+toward[0]*blend,point[1]+toward[1]*blend)
                    actual = self.region_at(candidate)
                    if actual is not None and actual['area'] is not None:
                        point = candidate
                        break
            if actual is not None and actual['area'] is not None:region = actual
            return self._select(point,region,introductory)
        return None

    def finish(self, receipt=None):
        """Complete one pending encounter and roll its next protected distance."""
        if self._pending is None:return False
        if receipt is not None and receipt != self._pending['receipt']:return False
        self._pending = None
        self._threshold = self._roll_distance()
        self._remaining = self._threshold
        self._was_safe = None
        return True

    def valid_ticket(self, record):
        intro = isinstance(record,dict) and record.get('lesson') == 'aqua_edge'
        fields = TICKET_FIELDS | {'lesson'} if intro else TICKET_FIELDS
        if (not isinstance(record,dict) or set(record) != fields
                or type(record['version']) is not int or record['version'] != 1
                or not isinstance(record['receipt'],str)
                or re.fullmatch(r'cave:[0-9a-f]{8}:[1-9][0-9]{0,9}',record['receipt']) is None
                or not isinstance(record['area'],str) or record['area'] not in AREAS
                or not isinstance(record['location'],str)
                or not isinstance(record['battlefield'],str) or record['battlefield'] not in BATTLEFIELDS
                or not isinstance(record['formation'],str) or record['formation'] not in self.data['formations']
                or not _integer(record['combat_seed']) or not isinstance(record['position'],list)
                or _point(record['position']) is None):return False
        region = self.region_at(record['position'])
        if region is None or any(record[k] != region[k] for k in ('area','location','battlefield')):return False
        area = self.data['areas'][record['area']]
        if intro:
            if record['formation'] != 'bat_pair':return False
        elif not area['weights'][record['formation']]:return False
        members = record['members']
        species = self.data['formations'][record['formation']]
        if not isinstance(members,list) or len(members) != len(species):return False
        for member,expected in zip(members,species):
            low, high = area['levels'][expected]
            old_low, old_high = LEGACY_LEVELS[record['area']].get(expected, (low, high))
            limits = (2, 2) if intro else (min(low, old_low), max(high, old_high))
            if (not isinstance(member,dict) or set(member) != {'enemy_id','level'} or member['enemy_id'] != expected
                    or not _integer(member['level'],*limits)):return False
        return True

    def to_dict(self):
        return {'version':1,'identity':self._identity,'rng_state':self._rng_state,
                'sequence':self._sequence,'threshold':self._threshold,
                'remaining':self._remaining,'was_safe':self._was_safe,'pending':self.pending}

    def _valid_state(self, record):
        if (not isinstance(record,dict) or set(record) != STATE_FIELDS
                or type(record['version']) is not int or record['version'] != 1
                or any(not _integer(record[k]) for k in ('identity','rng_state','sequence'))
                or not _number(record['threshold'],self.minimum_distance,self.maximum_distance)
                or not _number(record['remaining'],0,record['threshold'])
                or (record['was_safe'] is not None and type(record['was_safe']) is not bool)):
            return False
        pending = record['pending']
        if pending is None:return record['remaining'] > 0
        return (record['remaining'] == 0 and self.valid_ticket(pending)
                and pending['receipt'] == f"cave:{record['identity']:08x}:{record['sequence']}"
                and pending['combat_seed'] == record['rng_state'])

    def restore(self, record=None):
        if record is None:
            self.reset()
            return True
        try:
            if not self._valid_state(record):return False
        except (TypeError,ValueError,KeyError):return False
        record = deepcopy(record)
        self._identity,self._rng_state,self._sequence = (record[k] for k in ('identity','rng_state','sequence'))
        self._threshold,self._remaining = record['threshold'],record['remaining']
        self._was_safe,self._pending = record['was_safe'],record['pending']
        return True

    @classmethod
    def valid_snapshot(cls, record):
        try:return cls(seed=0)._valid_state(record)
        except (TypeError,ValueError,KeyError,OSError):return False

    @classmethod
    def valid_journey(cls, data):
        if not isinstance(data,dict):return False
        if SAVE_KEY not in data:return True
        try:
            owner = cls(seed=0)
            record = data[SAVE_KEY]
            if not owner._valid_state(record):return False
            if record['pending'] is None:return True
            player = data['player']
            lesson = data.get('cave_lesson')
            if (record['pending'].get('lesson') == 'aqua_edge'
                    and isinstance(lesson, dict) and lesson.get('deferred') is True):return True
            return player['scene'] == SCENE_ID and player['position'] == record['pending']['position']
        except (TypeError,ValueError,KeyError,OSError):return False


def valid_ticket(record):
    """Validate a detached battle handoff without constructing a game."""
    try:return CaveRandomEncounters(seed=0).valid_ticket(record)
    except (TypeError,ValueError,KeyError,OSError):return False
