"""Georeferenced illustrated chart tiles shared by the atlas and minimap.

The chart has its own bounded image cache. It never asks the gameplay world to
render terrain, load a scene, or allocate an image at the size of Auratia.
"""
from __future__ import annotations

from collections import OrderedDict
import hashlib
import json
import math
from pathlib import Path

import pygame


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT/'assets/cartography/elden_vale/manifest.json'
CACHE_BUDGET = 24*1024*1024
ICON_BUDGET = 2*1024*1024
LAND = '#99aa75'
WATER = '#739da8'


def region_data(value):
    if isinstance(value,dict):return value
    return getattr(value,'region',None) or value.data


def geometry_fingerprint(value):
    data = region_data(value)
    # Operational flags and prose do not invalidate the painted geography.
    keys = ('bounds_tiles','terrain','roads','walls')
    record = {key:data.get(key,[]) for key in keys}
    record['town'] = data.get('town',{}).get('tile_position')
    record['bridge'] = data.get('bridge',{}).get('tile_position')
    record['farms'] = [(s.get('id'),s.get('tile_position'))
                       for s in data.get('setpieces',[]) if s.get('kind')=='farmstead']
    encoded = json.dumps(record,sort_keys=True,separators=(',',':')).encode()
    return hashlib.sha256(encoded).hexdigest()


class _Images:
    def __init__(self,budget):
        self.budget = max(1,int(budget));self.bytes = 0;self.items = OrderedDict()
        self.loads = 0

    def get(self,key,loader):
        if key in self.items:
            self.items.move_to_end(key);return self.items[key]
        image = loader();self.loads += 1
        weight = image.get_pitch()*image.get_height()
        if weight > self.budget:return image
        self.items[key] = image;self.bytes += weight
        while self.bytes > self.budget:
            _,old = self.items.popitem(last=False)
            self.bytes -= old.get_pitch()*old.get_height()
        return image


def tile_to_pixel(point,rect,center,scale):
    return (rect.centerx+(point[0]-center[0])*scale,
            rect.centery+(point[1]-center[1])*scale)


def _outside(a,b,rect):
    """Split a line around a closed crossing, in source tile coordinates."""
    dx,dy = b[0]-a[0],b[1]-a[1];low,high = 0.0,1.0
    for origin,delta,start,end in ((a[0],dx,rect[0],rect[0]+rect[2]),
                                   (a[1],dy,rect[1],rect[1]+rect[3])):
        if not delta:
            if origin < start or origin > end:return [(a,b)]
            continue
        one,two = (start-origin)/delta,(end-origin)/delta
        low,high = max(low,min(one,two)),min(high,max(one,two))
        if low > high:return [(a,b)]
    result = []
    point = lambda t:(a[0]+dx*t,a[1]+dy*t)
    if low > 0:result.append((a,point(low)))
    if high < 1:result.append((point(high),b))
    return result


def _dash_parts(a,b,phase,scale,rect):
    """Display-size dashes retain one phase along a densified source path."""
    dx,dy = b[0]-a[0],b[1]-a[1];length = math.hypot(dx,dy)
    if not length:return
    low,high = 0.0,1.0
    for origin,delta,start,end in ((a[0],dx,rect.left-8,rect.right+8),
                                   (a[1],dy,rect.top-8,rect.bottom+8)):
        if not delta:
            if origin<start or origin>end:return
            continue
        one,two = (start-origin)/delta,(end-origin)/delta
        low,high = max(low,min(one,two)),min(high,max(one,two))
        if low>high:return
    # Phase is measured from the road's first authored point, never the clip.
    period,dash = 10.0,6.0
    beginning,ending = phase+low*length,phase+high*length
    for index in range(math.floor(beginning/period),math.ceil(ending/period)+1):
        start,end = max(beginning,index*period),min(ending,index*period+dash)
        if end<=start:continue
        t0,t1 = (start-phase)/length,(end-phase)/length
        first = (round(a[0]+dx*t0),round(a[1]+dy*t0))
        last = (round(a[0]+dx*t1),round(a[1]+dy*t1))
        # A zero-length wide pygame line adds a square beyond a dash end.
        # Dense curve samples often round onto the preceding endpoint.
        if first!=last:yield first,last


class RegionalCartography:
    def __init__(self,region_or_world,manifest_path=MANIFEST,*,cache_budget_bytes=CACHE_BUDGET):
        self.data = region_data(region_or_world)
        self.manifest_path = Path(manifest_path)
        self.signature = geometry_fingerprint(self.data)
        self.bounds = tuple(self.data.get('bounds_tiles',(-256,-192,512,384)))
        self.manifest = {}
        if self.manifest_path.is_file():
            self.manifest = json.loads(self.manifest_path.read_text(encoding='utf-8'))
        self.focus_bounds = self._focus()
        self._tiles = _Images(cache_budget_bytes)
        self._icons = _Images(ICON_BUDGET)
        self._art = {}
        art_path = self.manifest.get('art_manifest','assets/cartography/elden_vale/art/art.json')
        if (ROOT/art_path).is_file():self._art = json.loads((ROOT/art_path).read_text())
        self._tile_records = {(record['level'],record['x'],record['y']):record
                              for record in self.manifest.get('tiles',[])}
        self._compatible = self._matches()

    def _matches(self):
        return (self.manifest.get('geometry_sha256')==self.signature
                and tuple(self.manifest.get('bounds_tiles',()))==self.bounds)

    def _focus(self):
        if self.data.get('focus_bounds_tiles'):return tuple(self.data['focus_bounds_tiles'])
        same_region = self.data.get('region_id')==self.manifest.get('region_id')
        same_bounds = tuple(self.manifest.get('bounds_tiles',()))==self.bounds
        if same_region and same_bounds:
            return tuple(self.manifest.get('focus_bounds_tiles',self.bounds))
        if self.data.get('region_id')=='elden_vale_start' and self.bounds==(-256,-192,512,384):
            return (-140,-110,280,220)
        return self.bounds

    def refresh(self):
        """Explicit editor/map-open refresh; ordinary drawing hashes no data."""
        self.bounds = tuple(self.data.get('bounds_tiles',self.bounds))
        self.signature = geometry_fingerprint(self.data)
        self._compatible = self._matches()
        self.focus_bounds = self._focus()
        return self

    @property
    def art_available(self):return bool(self._tile_records)

    @property
    def compatible(self):return self._compatible

    @property
    def available(self):return self.art_available and self.compatible

    @property
    def cache_stats(self):
        return {'tile_bytes':self._tiles.bytes,'tile_count':len(self._tiles.items),
                'tile_budget':self._tiles.budget,'tile_loads':self._tiles.loads,
                'icon_bytes':self._icons.bytes,'icon_count':len(self._icons.items),
                'icon_budget':self._icons.budget}

    def _load_tile(self,key):
        record = self._tile_records[key]
        return self._tiles.get(key,lambda:pygame.image.load(str(ROOT/record['image'])).convert())

    def draw_terrain(self,target,map_rect,center_tiles,scale_px_per_tile):
        rect = pygame.Rect(map_rect);scale = float(scale_px_per_tile)
        if scale <= 0 or rect.width <= 0 or rect.height <= 0:return False
        old = target.get_clip();target.set_clip(rect.clip(old))
        try:
            target.fill(LAND,rect)
            if not self.available:
                self._fallback(target,rect,center_tiles,scale);return False
            density = float(self.manifest['pixels_per_tile'])
            # Choose a mip which is not smaller than its display footprint.
            ratio = density/scale
            levels = sorted(self.manifest['levels'])
            level = max((n for n in levels if n<=ratio),default=levels[0])
            pixels_per_tile = density/level
            tile_size = self.manifest['tile_size']
            map_left = center_tiles[0]-rect.width/(2*scale)
            map_top = center_tiles[1]-rect.height/(2*scale)
            map_right = center_tiles[0]+rect.width/(2*scale)
            map_bottom = center_tiles[1]+rect.height/(2*scale)
            bx,by,bw,bh = self.bounds
            # Clamp the visible ranges before iterating, even for huge bounds.
            x0 = max(0,math.floor((max(bx,map_left)-bx)*pixels_per_tile/tile_size))
            y0 = max(0,math.floor((max(by,map_top)-by)*pixels_per_tile/tile_size))
            x1 = min(math.ceil(bw*pixels_per_tile/tile_size),
                     math.ceil((min(bx+bw,map_right)-bx)*pixels_per_tile/tile_size))
            y1 = min(math.ceil(bh*pixels_per_tile/tile_size),
                     math.ceil((min(by+bh,map_bottom)-by)*pixels_per_tile/tile_size))
            for cy in range(y0,y1):
                for cx in range(x0,x1):
                    key = (level,cx,cy)
                    if key not in self._tile_records:continue
                    image = self._load_tile(key)
                    left = bx+cx*tile_size/pixels_per_tile
                    top = by+cy*tile_size/pixels_per_tile
                    right = left+image.get_width()/pixels_per_tile
                    bottom = top+image.get_height()/pixels_per_tile
                    a = tile_to_pixel((left,top),rect,center_tiles,scale)
                    b = tile_to_pixel((right,bottom),rect,center_tiles,scale)
                    # Identical rounded endpoints prevent transparent tile seams.
                    dest = pygame.Rect(round(a[0]),round(a[1]),
                                       max(1,round(b[0])-round(a[0])),
                                       max(1,round(b[1])-round(a[1])))
                    if not dest.colliderect(rect):continue
                    if image.get_size()!=dest.size:image = pygame.transform.scale(image,dest.size)
                    target.blit(image,dest)
            return True
        finally:target.set_clip(old)

    def _fallback(self,target,rect,center,scale):
        colors = {'forests':'#6f8e62','fields':'#b1ac72','hills':'#aaa47c'}
        for group in ('fields','forests','hills'):
            for item in self.data.get('terrain',{}).get(group,[]):
                points = [tile_to_pixel(p,rect,center,scale) for p in item.get('polygon',[])]
                if len(points)>=3:pygame.draw.polygon(target,colors[group],points)
        for river in self.data.get('terrain',{}).get('rivers',[]):
            points = [tile_to_pixel(p,rect,center,scale) for p in river.get('points',[])]
            if len(points)>1:
                pygame.draw.lines(target,WATER,False,points,max(1,round(river.get('width',10)*scale)))

    def draw_routes(self,target,map_rect,center_tiles,scale_px_per_tile,flags=()):
        rect = pygame.Rect(map_rect);scale = float(scale_px_per_tile)
        old = target.get_clip();target.set_clip(rect.clip(old))
        flags = set(flags)
        try:
            bridge = self.data.get('bridge',{})
            blocked = (bridge.get('damage_rect_tiles') if bridge and
                       bridge.get('repair_flag') not in flags else None)
            for road in sorted(self.data.get('roads',[]),key=lambda r:{'foot':0,'cart':1,'stone':2}.get(r.get('kind'),1)):
                kind = road.get('kind','cart')
                width = (max(3,round(scale*.95)) if kind=='stone' else
                         max(2,round(scale*.55)) if kind=='cart' else max(1,round(scale*.28)))
                color = '#e5d6b8' if kind=='stone' else '#cbb186' if kind=='cart' else '#d2c19a'
                phase = 0.0
                for a,b in zip(road.get('points',[]),road.get('points',[])[1:]):
                    for start,end in (_outside(a,b,blocked) if blocked else [(a,b)]):
                        p = tile_to_pixel(start,rect,center_tiles,scale)
                        q = tile_to_pixel(end,rect,center_tiles,scale)
                        if kind=='foot':
                            offset = math.dist(a,start)*scale
                            for first,last in _dash_parts(p,q,phase+offset,scale,rect):
                                pygame.draw.line(target,'#8c805f',first,last,width+1)
                                pygame.draw.line(target,color,first,last,width)
                        else:
                            pygame.draw.line(target,'#87795c' if kind=='stone' else '#97825f',p,q,width+2 if kind=='stone' else width+1)
                            pygame.draw.line(target,color,p,q,width)
                    phase += math.dist(a,b)*scale
            for wall in self.data.get('walls',[]):
                gate = wall.get('gate_x',wall['x0']);half = wall.get('gate_width',0)/2
                spans = [(wall['x0'],gate-half),(gate+half,wall['x1'])] if half else [(wall['x0'],wall['x1'])]
                for left,right in spans:
                    a = tile_to_pixel((left,wall['y']),rect,center_tiles,scale)
                    b = tile_to_pixel((right,wall['y']),rect,center_tiles,scale)
                    width = max(1,min(4,round(scale*.55)))
                    pygame.draw.line(target,'#53645b',a,b,width+1)
                    pygame.draw.line(target,'#c2c2ab',a,b,width)
        finally:target.set_clip(old)

    def icon(self,key,size=None):
        record = self._art.get('props',{}).get(key)
        if record is None:return None
        if size is None:size = (64,64)
        elif isinstance(size,(int,float)):size = (size,size)
        size = tuple(max(1,min(256,int(n))) for n in size)
        def load():
            raw = pygame.image.load(str(ROOT/record['image'])).convert_alpha()
            bounds = raw.get_bounding_rect()
            if bounds.width and bounds.height:raw = raw.subsurface(bounds).copy()
            factor = min(size[0]/raw.get_width(),size[1]/raw.get_height())
            return pygame.transform.scale(raw,(max(1,round(raw.get_width()*factor)),
                                               max(1,round(raw.get_height()*factor))))
        return self._icons.get((key,size),load)


def get_cartography(game,refresh=False):
    world = game.world;data = region_data(world)
    chart = getattr(game,'_regional_cartography',None)
    if chart is None or chart.data is not data or tuple(data.get('bounds_tiles',()))!=chart.bounds:
        chart = game._regional_cartography = RegionalCartography(world)
    elif refresh:chart.refresh()
    return chart
