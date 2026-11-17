"""Native regional material composition over existing vector geometry.

This module changes presentation only. Roads and rivers retain their authored
logical masks; globally anchored material phases survive signed chunk/camera
boundaries. Authored bank tiles supply detail outside the exact water footprint.
"""
from __future__ import annotations
import json
import math
from pathlib import Path
import pygame
from rendering import artwork, layer, rotate, scale, SurfaceCache, draw

ROOT = Path(__file__).resolve().parent
TILE = 24
CHUNK = 384
NEIGHBORS = ((0,-1,1),(1,-1,2),(1,0,4),(1,1,8),(0,1,16),(-1,1,32),(-1,0,64),(-1,-1,128))


def canonical_mask(raw):
    for diagonal, first, second in ((2,1,4),(8,4,16),(32,16,64),(128,64,1)):
        if not raw & first or not raw & second:
            raw &= ~diagonal
    return raw


def tile_phase(tx, ty):
    return tx % 2 + 2 * (ty % 2)


class RegionalTerrainHD:
    """Opt-in compositor used only when ``region.terrain_hd.enabled`` is true.

    ``world`` supplies image loading, existing path rasterization, art records
    and bridge state. All masks remain logical; WorldCanvas adapters rasterize
    them directly at native density.
    """
    def __init__(self, world):
        self.world = world
        self.config = world.region.get('terrain_hd', {})
        self._assets = SurfaceCache(8 * 1024 * 1024)
        self._mask_cache = SurfaceCache(8 * 1024 * 1024)
        self.grass_root = ROOT/'assets/terrain/eldenmere/grass_dirt_hd'
        self.stone_root = ROOT/'assets/terrain/eldenmere/stone_paving_hd'
        self.water_root = ROOT/'assets/terrain/water_hd'
        self.water_manifest = json.loads((self.water_root/'tileset.json').read_text())
        self.water_fields = {(record['depth'], record['texture_phase']): record
                             for record in self.water_manifest['water_surfaces']
                             if record['family'] == 'temperate' and record['arrangement'] == 0}
        self.bank_files = {(record['family'],record['mask']): record['file']
                           for record in self.water_manifest['bank_tiles'] if record['arrangement'] == 0}

    def _load(self, path):
        path = Path(path)
        cached = self._assets.get(str(path))
        if cached is not None:
            return cached
        image = pygame.image.load(str(path)).convert_alpha()
        image = artwork(image, 2)
        self._assets[str(path)] = image
        return image

    def _tile(self, key, tx, ty, frame=0, depth='deep'):
        grass = {'grass':'lawn_00','grass_meadow':'meadow_00',
                 'grass_lush':'lawn_01','forest_floor':'sheltered_00'}
        dirt = {'dirt':'dirt_00','cart_earth':'dirt_00','bank':'dirt_01'}
        if key in grass:
            return self._load(self.grass_root/'materials'/f'{grass[key]}.png')
        if key in dirt:
            # Coherent 4x4 tile patches rather than per-tile noise.
            variant = ((tx//4) + (ty//4)*3) % 4 if key == 'dirt' else int(dirt[key][-2:])
            return self._load(self.grass_root/'materials'/f'dirt_{variant:02}.png')
        if key in ('stone_road','stone_road_worn'):
            return self._load(self.stone_root/'surface'/f'phase_{tile_phase(tx,ty)}.png')
        if key == 'water':
            record = self.water_fields[depth,tile_phase(tx,ty)]
            return self._load(self.water_root/record['frames'][frame % len(record['frames'])]['file'])
        return self.world._tile_image(key)

    def pattern(self, target, key, origin, angle=0, *, frame=0, depth='deep'):
        """Fill a bounded target with phase-correct native artwork."""
        angle = round(float(angle)) % 360
        width,height = target.get_size()
        ox,oy = origin
        if not angle or key in ('water','stone_road','stone_road_worn'):
            for tx in range(math.floor(ox/TILE), math.ceil((ox+width)/TILE)):
                for ty in range(math.floor(oy/TILE), math.ceil((oy+height)/TILE)):
                    target.blit(self._tile(key,tx,ty,frame,depth),
                                (tx*TILE-ox,ty*TILE-oy))
            return
        # Flat agricultural surfaces follow their existing row angles. Structure
        # and water art never rotates; their lighting and spatial phases stay fixed.
        radians = math.radians(angle)
        c,s = math.cos(radians),math.sin(radians)
        if not angle % 90:
            c,s = round(c),round(s)
        corners = [(ox,oy),(ox+width,oy),(ox,oy+height),(ox+width,oy+height)]
        us = [x*c+y*s for x,y in corners]
        vs = [-x*s+y*c for x,y in corners]
        for tx in range(math.floor(min(us)/TILE)-1,math.ceil(max(us)/TILE)+1):
            for ty in range(math.floor(min(vs)/TILE)-1,math.ceil(max(vs)/TILE)+1):
                image = self._tile(key,tx,ty)
                cache_key = ('rotated',key,angle,id(image))
                tile = self._assets.get(cache_key)
                if tile is None:
                    tile = rotate(scale(image,(25,25)) if angle % 90 else image,-angle)
                    self._assets[cache_key] = tile
                x=(tx+.5)*TILE*c-(ty+.5)*TILE*s-ox
                y=(tx+.5)*TILE*s+(ty+.5)*TILE*c-oy
                target.blit(tile,(round(x-tile.get_width()/2),round(y-tile.get_height()/2)))

    def paint(self, target, key, painter, origin, angle=0):
        """Clip material in both grids, never through a logical-only overlay."""
        overlay = layer(target.get_size())
        mask = layer(target.get_size())
        self.pattern(overlay,key,origin,angle)
        painter(mask)
        overlay.blit(mask,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
        target.blit(overlay,(0,0))
        if key in ('dirt','cart_earth','stone_road','stone_road_worn'):
            self._contact_shadow(target,mask)

    @staticmethod
    def _contact_shadow(target, mask):
        """A one-world-unit inner contact shade follows the authored mask.

        It darkens the existing material/substrate boundary without expanding
        path width, snapping geometry or outlining individual terrain tiles.
        """
        bounds=mask.get_bounding_rect().inflate(4,4).clip(mask.get_rect())
        if not bounds:return
        local=mask.subsurface(bounds)
        interior=local.copy()
        for offset in ((-1,0),(1,0),(0,-1),(0,1)):
            shifted=layer(bounds.size)
            shifted.blit(local,offset)
            # Continue the edge texels beyond a clipped chunk, rather than
            # treating the crop as transparent ground. Real material boundaries
            # along that edge retain their shade; no vertical crop seam appears.
            if offset[0]>0 and bounds.left==0:
                shifted.blit(local,(0,0),(0,0,1,bounds.height))
            if offset[0]<0 and bounds.right==mask.get_width():
                shifted.blit(local,(bounds.width-1,0),(bounds.width-1,0,1,bounds.height))
            if offset[1]>0 and bounds.top==0:
                shifted.blit(local,(0,0),(0,0,bounds.width,1))
            if offset[1]<0 and bounds.bottom==mask.get_height():
                shifted.blit(local,(0,bounds.height-1),(0,bounds.height-1,bounds.width,1))
            interior.blit(shifted,(0,0),special_flags=pygame.BLEND_RGBA_MIN)
        edge=local.copy()
        edge.blit(interior,(0,0),special_flags=pygame.BLEND_RGBA_SUB)
        shade=layer(bounds.size)
        shade.fill((0,0,0,30))
        shade.blit(edge,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
        target.blit(shade,bounds.topleft)

    def _path_mask(self, size, origin, river, extra=0):
        mask = layer(size)
        points = [(round(x*TILE-origin[0]),round(y*TILE-origin[1])) for x,y in river['points']]
        width = max(1,river.get('width',8)*TILE+extra)
        self.world._draw_path(mask,'white',points,width)
        return mask

    @staticmethod
    def _near_water(point, segments, radius):
        x,y=point
        for a,b in segments:
            dx,dy=b[0]-a[0],b[1]-a[1]
            length=dx*dx+dy*dy
            t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/length)) if length else 0
            if (x-a[0]-t*dx)**2+(y-a[1]-t*dy)**2 <= radius*radius:
                return True
        return False

    def bank(self, target, river, cx, cy):
        """Natural shore detail stays outside the exact vector water mask."""
        # Rasterize beyond the crop before clipping. Native polygon edge rules
        # otherwise differ by a texel when a curved shore meets a chunk edge.
        pad=4
        scratch=layer((target.get_width()+pad*2,target.get_height()+pad*2))
        self._bank(scratch,river,(cx*CHUNK-pad,cy*CHUNK-pad))
        target.blit(scratch.subsurface((pad,pad,*target.get_size())),(0,0))

    def _bank(self,target,river,origin):
        outer = self._path_mask(target.get_size(),origin,river,22)
        # Match the regional painter's globally phased, irregular dry margins.
        # These are material-mask details only; water/collision remains exact.
        from overworld_environment import samples, stable
        global_points=[(x*TILE,y*TILE) for x,y in river['points']]
        viewport=pygame.Rect(origin,target.get_size())
        half_width=river.get('width',8)*TILE/2
        for point,normal,index,_ in samples(global_points,13,viewport,half_width+32):
            seed=stable(index,63,43)
            for side in (-1,1):
                distance=half_width+6+seed%5
                center=(round(point[0]+normal[0]*distance*side-origin[0]),
                        round(point[1]+normal[1]*distance*side-origin[1]))
                draw.circle(outer,'white',center,3+seed%4)
        water = self._path_mask(target.get_size(),origin,river)
        dry = outer.copy()
        dry.blit(water,(0,0),special_flags=pygame.BLEND_RGBA_SUB)
        underlay = layer(target.get_size())
        self.pattern(underlay,'bank',origin)
        underlay.blit(dry,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
        target.blit(underlay,(0,0))
        # The original 47-shape bank art is globally phased on the material grid.
        # Its outer alpha is clipped back to the exact dry strip, so grid choices
        # never change the visible water/collision boundary.
        radius = river.get('width',8)/2
        tiles_w=math.ceil(target.get_width()/TILE)
        tiles_h=math.ceil(target.get_height()/TILE)
        tx0,ty0=math.floor(origin[0]/TILE),math.floor(origin[1]/TILE)
        view = pygame.Rect(tx0-2,ty0-2,tiles_w+4,tiles_h+4).inflate(math.ceil(radius*2),math.ceil(radius*2))
        segments=[]
        for a,b in zip(river['points'],river['points'][1:]):
            bounds=pygame.Rect(math.floor(min(a[0],b[0])),math.floor(min(a[1],b[1])),
                               max(1,math.ceil(abs(a[0]-b[0]))),max(1,math.ceil(abs(a[1]-b[1]))))
            if view.colliderect(bounds):segments.append((a,b))
        family=river.get('bank_family',self.config.get('bank_family','grass'))
        if family not in self.water_manifest['bank_families']:
            family='grass'
        overlay=layer(target.get_size())
        occupied={}
        def wet(tx,ty):
            key=tx,ty
            if key not in occupied:occupied[key]=self._near_water((tx+.5,ty+.5),segments,radius)
            return occupied[key]
        for tx in range(tx0-1,tx0+tiles_w+1):
            for ty in range(ty0-1,ty0+tiles_h+1):
                if not wet(tx,ty):continue
                raw=sum(bit for dx,dy,bit in NEIGHBORS if wet(tx+dx,ty+dy))
                normalized=canonical_mask(raw)
                if normalized==255:continue
                image=self._load(self.water_root/self.bank_files[family,normalized])
                overlay.blit(image,(tx*TILE-origin[0],ty*TILE-origin[1]))
        overlay.blit(dry,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
        target.blit(overlay,(0,0))

    def _water_masks(self, size, camera):
        key=tuple(size),tuple(camera),bool(self.world._bridge_repaired())
        found=self._mask_cache.get(key)
        cached_deep=self._mask_cache.get(('deep',)+key)
        if found is not None and cached_deep is not None:
            return found,cached_deep
        pad=4
        padded_size=(size[0]+pad*2,size[1]+pad*2)
        padded_camera=(camera[0]-pad,camera[1]-pad)
        water=layer(padded_size)
        deep=layer(padded_size)
        view=pygame.Rect(padded_camera,padded_size)
        for river in self.world.region.get('terrain',{}).get('rivers',[]):
            if not self.world._feature_intersects(river['points'],view,river.get('width',8)*TILE/2+2):continue
            water.blit(self._path_mask(padded_size,padded_camera,river),(0,0))
            # Several narrow native-opacity bands avoid an abrupt shallow/deep
            # stripe while preserving the exact outer river mask.
            points=[(round(x*TILE-padded_camera[0]),round(y*TILE-padded_camera[1])) for x,y in river['points']]
            for inset,alpha in ((6,40),(11,85),(16,145),(21,205),(26,255)):
                width=river.get('width',8)*TILE-inset*2
                if width>0:self.world._draw_path(deep,(255,255,255,alpha),points,width)
        water=water.subsurface((pad,pad,*size)).copy()
        deep=deep.subsurface((pad,pad,*size)).copy()
        bridge=self.world.region.get('bridge')
        if bridge and self.world._bridge_repaired():
            rect=self.world._tile_rect(bridge.get('deck_rect_tiles',bridge['damage_rect_tiles'])).move(-camera[0],-camera[1])
            water.fill((0,0,0,0),rect)
            deep.fill((0,0,0,0),rect)
        self._mask_cache[key]=water
        # Deep masks are cheap and cannot share SurfaceCache entries with tuples.
        self._mask_cache[('deep',)+key]=deep
        return water,deep

    def draw_water(self, target, camera, elapsed_ms, reduced_motion=False):
        """Native six-frame water beneath props, with shallow edges and dry deck."""
        water,deep=self._water_masks(target.get_size(),camera)
        if not water.get_bounding_rect():return
        frame=0 if reduced_motion else int(max(0,elapsed_ms)//200)%6
        overlay=layer(target.get_size())
        self.pattern(overlay,'water',camera,frame=frame,depth='shallow')
        overlay.blit(water,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
        target.blit(overlay,(0,0))
        if deep is not None:
            overlay=layer(target.get_size())
            self.pattern(overlay,'water',camera,frame=frame,depth='deep')
            overlay.blit(deep,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
            target.blit(overlay,(0,0))
