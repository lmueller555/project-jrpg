"""Small, deterministic environment compositions for the streamed overworld.

Art stays in the native generated asset kit. This module places that art and
clips materials to authored terrain; it never allocates a region-sized image.
"""
from __future__ import annotations

from collections import defaultdict
import math

import pygame


TILE = 24
CHUNK = 384


def stable(x, y, salt=0):
    value = (int(x)*0x1f123bb5 ^ int(y)*0x5f356495 ^ int(salt)*0x45d9f3b) & 0xffffffff
    value ^= value >> 16;value = value*0x7feb352d & 0xffffffff
    value ^= value >> 15;value = value*0x846ca68b & 0xffffffff
    return value ^ (value >> 16)


def inside(point, polygon):
    x,y = point;result = False
    for a,b in zip(polygon,polygon[1:]+polygon[:1]):
        if (a[1] > y) != (b[1] > y):
            if x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:result = not result
    return result


def path_distance(point, points):
    result = math.inf
    for a,b in zip(points,points[1:]):
        dx,dy = b[0]-a[0],b[1]-a[1];length2 = dx*dx+dy*dy
        t = 0 if not length2 else max(0,min(1,((point[0]-a[0])*dx+(point[1]-a[1])*dy)/length2))
        result = min(result,math.hypot(point[0]-a[0]-t*dx,point[1]-a[1]-t*dy))
    return result


def samples(points, step, viewport, padding=16):
    """Globally phased path samples, clipped before iteration to this chunk."""
    clip = viewport.inflate(padding*2,padding*2)
    distance = 0.0
    for segment,(a,b) in enumerate(zip(points,points[1:])):
        dx,dy = b[0]-a[0],b[1]-a[1];length = math.hypot(dx,dy)
        if not length:continue
        clipped = clip.clipline((round(a[0]),round(a[1])),(round(b[0]),round(b[1])))
        if clipped:
            t0 = max(0,min(1,((clipped[0][0]-a[0])*dx+(clipped[0][1]-a[1])*dy)/(length*length)))
            t1 = max(0,min(1,((clipped[1][0]-a[0])*dx+(clipped[1][1]-a[1])*dy)/(length*length)))
            first = math.ceil((distance+min(t0,t1)*length)/step)
            last = math.floor((distance+max(t0,t1)*length)/step)
            for index in range(first,last+1):
                t = (index*step-distance)/length
                yield (a[0]+t*dx,a[1]+t*dy),(-dy/length,dx/length),index,segment
        distance += length


class EnvironmentDetail:
    def __init__(self, world):
        self.world = world
        self.by_chunk = defaultdict(list)
        self.solid_by_chunk = defaultdict(list)
        self.paths_by_chunk = defaultdict(list)
        self.roads_by_chunk = defaultdict(list)
        self._textures = {}
        self._safe_rects = [world._tile_rect(item['rect_tiles'])
                            for item in world.region.get('safe_clearings',[])]
        paths = [(road,road.get('width',3)/2+1.3,True) for road in world.region.get('roads',[])]
        paths += [(river,river.get('width',8)/2+1.3,False)
                  for river in world.region.get('terrain',{}).get('rivers',[])]
        paths += [(path,path.get('width',2)/2+.5,False)
                  for path in world.region.get('clearance_paths',[])]
        for path,radius,is_road in paths:
            for a,b in zip(path['points'],path['points'][1:]):
                for cx in range(math.floor((min(a[0],b[0])-radius)/16),math.floor((max(a[0],b[0])+radius)/16)+1):
                    for cy in range(math.floor((min(a[1],b[1])-radius)/16),math.floor((max(a[1],b[1])+radius)/16)+1):
                        self.paths_by_chunk[(cx,cy)].append((a,b,radius))
                        if is_road:self.roads_by_chunk[(cx,cy)].append((a,b,radius))
        records = list(world.region.get('decorations',[]))
        for scene in world.region.get('setpieces',[]):records.extend(scene.get('props',[]))
        self.authored = []
        for index,record in enumerate(records):
            prop = {**record,'id':record.get('id',f'authored:{index}'),
                    'position':world._tile_point(record['tile_position']),'authored':True}
            self.authored.append(prop)
            x,y = prop['position']
            self.by_chunk[(math.floor(x/CHUNK),math.floor(y/CHUNK))].append(prop)
            if prop.get('solid'):
                width,height = prop['solid']
                rect = pygame.Rect(round(x)-width//2,round(y)-height//2,width,height)
                for cx in range(rect.left//CHUNK,(rect.right-1)//CHUNK+1):
                    for cy in range(rect.top//CHUNK,(rect.bottom-1)//CHUNK+1):
                        self.solid_by_chunk[(cx,cy)].append(prop)

    def key(self, preferred, fallback):
        return preferred if preferred in self.world._art.get('tiles',{}) else fallback

    def prop_key(self, preferred, fallback):
        return preferred if preferred in self.world._art.get('props',{}) else fallback

    def _reserved(self, point, padding=0):
        pixel = self.world._tile_point(point)
        if self.world.town_entry_rect.inflate(5*TILE,5*TILE).collidepoint(pixel):return True
        if any(rect.collidepoint(pixel) for rect in self._safe_rects):return True
        chunk = (math.floor(point[0]/16),math.floor(point[1]/16))
        for a,b,radius in self.paths_by_chunk.get(chunk,()):
            if path_distance(point,(a,b)) < radius+padding/TILE:return True
        for wall in self.world.region.get('walls',[]):
            if wall['x0']-3 <= point[0] <= wall['x1']+3 and abs(point[1]-wall['y']) < 4:return True
        # Keep spontaneous trees away from the whole farm composition, rather
        # than letting them grow through gardens, hedges and miniature roofs.
        for scene in self.world.region.get('setpieces',[]):
            center = scene.get('tile_position')
            if center and math.dist(point,center) < scene.get('clearance_radius',7):return True
        return False

    def _grove_props(self, cx, cy):
        """Each loose stand owns several overlapping crowns and open margins.

        Grove centres live on a coarse global lattice, but their full-cell
        jitter, variable radii and uneven children make the visible trees form
        masses rather than rows. Feet, not centre cells, own the final props.
        """
        forests = self.world.region.get('terrain',{}).get('forests',[])
        if not forests:return
        view = pygame.Rect(cx*CHUNK,cy*CHUNK,CHUNK,CHUNK)
        if not any(self.world._feature_intersects(f['polygon'],view,4*TILE) for f in forests):return
        left,top,right,bottom = cx*16,cy*16,(cx+1)*16,(cy+1)*16
        for gx in range(math.floor((left-4)/8),math.ceil((right+4)/8)):
            for gy in range(math.floor((top-4)/8),math.ceil((bottom+4)/8)):
                seed = stable(gx,gy,211)
                center = (gx*8+1.2+(seed%560)/100,
                          gy*8+1.2+((seed>>9)%560)/100)
                forest = next((f for f in forests if inside(center,f['polygon'])),None)
                if forest is None:continue
                density = forest.get('density','medium')
                chance = {'sparse':50,'medium':76,'dense':94}.get(density,76)
                if seed%100 >= chance:continue
                count = {'sparse':4,'medium':7,'dense':10}.get(density,7)+(seed>>17)%3
                radius = 1.65+((seed>>13)%95)/100
                style = forest.get('style',forest.get('kind','broadleaf'))
                stand_conifer = style == 'conifer' or (style == 'mixed' and (seed>>11)%4 == 0)
                for child in range(count):
                    branch = stable(gx,gy,child+231)
                    angle = ((seed>>7)%360)*math.pi/180+child*2.399963
                    reach = radius*math.sqrt((child+.4)/count)*(.82+(branch%35)/100)
                    point = (center[0]+math.cos(angle)*reach,
                             center[1]+math.sin(angle)*reach)
                    if (math.floor(point[0]/16),math.floor(point[1]/16)) != (cx,cy):continue
                    if not inside(point,forest['polygon']) or self._reserved(point):continue
                    conifer = stand_conifer or (style == 'mixed' and branch%13 == 0)
                    choices = ('conifer_a','conifer_b') if conifer else ('oak_a','oak_b','oak_c')
                    fallback = 'tree_conifer' if conifer else 'tree_broadleaf'
                    variant = (seed>>20)%len(choices) if child%4 else (branch>>10)%len(choices)
                    key = self.prop_key(choices[variant],fallback)
                    grove_id = f'stand:{gx}:{gy}'
                    yield {'id':f'{grove_id}:tree:{child}','key':key,
                           'position':self.world._tile_point(point),'solid':(12,8),
                           'grove_id':grove_id,'crown_ground':True}
                    if child%3 == 0:
                        bush = (point[0]+.55,point[1]+.35)
                        if ((math.floor(bush[0]/16),math.floor(bush[1]/16)) == (cx,cy)
                                and inside(bush,forest['polygon']) and not self._reserved(bush)):
                            kind = ('fern','shrub','sapling','log','stump')[(branch>>15)%5]
                            yield {'id':f'{grove_id}:floor:{child}',
                                   'key':self.prop_key(kind,'rock'),
                                   'position':self.world._tile_point(bush),'grove_id':grove_id}

    def chunk_props(self, cx, cy):
        props = list(self.by_chunk.get((cx,cy),()))
        props.extend(self._grove_props(cx,cy))
        terrain = self.world.region.get('terrain',{})
        # Small meadow details and legacy hill fixtures stay sparse. Actual
        # forest trees come from the composed stands above.
        for gx in range(math.floor(cx*16/3)*3,math.ceil((cx+1)*16/3)*3,3):
            for gy in range(math.floor(cy*16/3)*3,math.ceil((cy+1)*16/3)*3,3):
                for candidate in range(2):
                    seed = stable(gx,gy,candidate+17)
                    point = (gx+.15+(seed%270)/100,gy+.15+((seed>>9)%270)/100)
                    if (math.floor(point[0]/16),math.floor(point[1]/16)) != (cx,cy):continue
                    if self._reserved(point):continue
                    forest = next((f for f in terrain.get('forests',[]) if inside(point,f['polygon'])),None)
                    if not forest:
                        hill = next((h for h in terrain.get('hills',[]) if inside(point,h['polygon'])),None)
                        if hill and hill.get('ground_treatment') == 'localized':continue
                        if hill and seed%7 == 0:
                            east = hill.get('style') == 'rocky_ridge' and point[0] > 70
                            xs = [p[0] for p in hill['polygon']]
                            center = (min(xs)+max(xs))/2+math.sin(point[1]*.09)*3
                            ridge = east and abs(point[0]-center)<6 and candidate == 0
                            key = self.prop_key('ridge' if ridge else 'rock_outcrop','rock')
                            props.append({'id':f'outcrop:{gx}:{gy}:{candidate}','key':key,
                                          'position':self.world._tile_point(point),'solid':(18,8)})
                        elif seed%17 == 0:
                            # Small meadow details are deliberately quiet; the
                            # composed yards and woodland remain the focal points.
                            key = self.prop_key(('grass_tuft','flowers_a','flowers_b')[seed%3],'rock')
                            if key != 'rock':props.append({'id':f'meadow:{gx}:{gy}:{candidate}',
                                                          'key':key,'position':self.world._tile_point(point)})
        # Generated riverbank plants use the actual path normal and stay outside
        # its solid water, so they follow bends instead of a rectangular grid.
        viewport = pygame.Rect(cx*CHUNK,cy*CHUNK,CHUNK,CHUNK)
        # Authored bank conditions own the plants at selected bends. Legacy
        # manifests retain the sparse automatic shoreline decoration.
        rivers = [] if terrain.get('shore_conditions') else terrain.get('rivers',[])
        for river_index,river in enumerate(rivers):
            points = [self.world._tile_point(p) for p in river['points']]
            for point,normal,index,_ in samples(points,72,viewport,200):
                seed = stable(index,river_index,91)
                for side in (-1,1):
                    if (seed+side)%3:continue
                    distance = river.get('width',8)*TILE/2+13+(seed%13)
                    x,y = point[0]+normal[0]*distance*side,point[1]+normal[1]*distance*side
                    if (math.floor(x/CHUNK),math.floor(y/CHUNK)) != (cx,cy):continue
                    tile = (x/TILE,y/TILE)
                    if any(path_distance(tile,(a,b))<radius for a,b,radius in self.roads_by_chunk.get((cx,cy),())):continue
                    key = self.prop_key('reeds' if seed%4 else 'river_rocks','rock')
                    props.append({'id':f'bank:{river_index}:{index}:{side}','key':key,'position':(x,y)})
        # Small plants soften woodland boundaries and road shoulders. Their
        # feet are decorative, allowing a close, readable verge without forcing
        # the much wider safety margin used by solid tree trunks.
        for forest_index,forest in enumerate(terrain.get('forests',[])):
            points = [self.world._tile_point(p) for p in forest['polygon']]
            points += points[:1]
            for point,normal,index,_ in samples(points,66,viewport,36):
                seed = stable(index,forest_index,104)
                if seed%3:continue
                x,y = point[0]+normal[0]*(seed%13-6),point[1]+normal[1]*(seed%13-6)
                if (math.floor(x/CHUNK),math.floor(y/CHUNK)) != (cx,cy):continue
                tile = (x/TILE,y/TILE)
                if any(path_distance(tile,(a,b))<radius-.8 for a,b,radius in self.roads_by_chunk.get((cx,cy),())):continue
                key = self.prop_key(('fern','shrub','sapling')[(seed>>7)%3],'rock')
                if key != 'rock':props.append({'id':f'fringe:{forest_index}:{index}','key':key,'position':(x,y)})
        for road_index,road in enumerate(self.world.region.get('roads',[])):
            points = [self.world._tile_point(p) for p in road['points']]
            for point,normal,index,_ in samples(points,90,viewport,70):
                seed = stable(index,road_index,109)
                if seed%3:continue
                side = -1 if seed%2 else 1;distance = road.get('width',3)*TILE/2+9+seed%11
                x,y = point[0]+normal[0]*distance*side,point[1]+normal[1]*distance*side
                if (math.floor(x/CHUNK),math.floor(y/CHUNK)) != (cx,cy):continue
                tile = (x/TILE,y/TILE)
                if any(path_distance(tile,r['points'])<r.get('width',8)/2+.2 for r in terrain.get('rivers',[])):continue
                key = self.prop_key(('grass_tuft','flowers_a','flowers_b')[(seed>>7)%3],'rock')
                if key != 'rock':props.append({'id':f'verge:{road_index}:{index}','key':key,'position':(x,y)})
        return props

    def collision_props(self, cx, cy):
        yield from self.solid_by_chunk.get((cx,cy),())
        # Procedural trunks can sit within a few pixels of their ownership seam.
        chunk = pygame.Rect(cx*CHUNK,cy*CHUNK,CHUNK,CHUNK)
        for nx in range(cx-1,cx+2):
            for ny in range(cy-1,cy+2):
                metadata = self.world._chunk_metadata(nx,ny)
                if metadata is None:continue
                for prop in metadata['props']:
                    if prop.get('authored') or not prop.get('solid'):continue
                    width,height = prop['solid'];x,y = prop['position']
                    if chunk.colliderect(pygame.Rect(round(x)-width//2,round(y)-height//2,width,height)):
                        yield prop

    def pattern(self, target, key, origin, angle=0):
        angle = round(float(angle))%360
        if not angle:
            self.world._pattern(target,key);return
        cache_key = key,angle
        if cache_key not in self._textures:
            # One-pixel overlap prevents raster cracks between rotated native
            # material swatches. The swatches themselves stay unmodified.
            tile = self.world._tile_image(key).convert_alpha()
            if angle%90:tile = pygame.transform.scale(tile,(25,25))
            self._textures[cache_key] = pygame.transform.rotate(tile,-angle)
        tile = self._textures[cache_key]
        radians = math.radians(angle);c,s = math.cos(radians),math.sin(radians)
        if not angle%90:c,s = round(c),round(s)
        width,height = target.get_size();ox,oy = origin
        corners = [(ox,oy),(ox+width,oy),(ox,oy+height),(ox+width,oy+height)]
        u = [x*c+y*s for x,y in corners];v = [-x*s+y*c for x,y in corners]
        for tx in range(math.floor(min(u)/24)-1,math.ceil(max(u)/24)+1):
            for ty in range(math.floor(min(v)/24)-1,math.ceil(max(v)/24)+1):
                x = (tx+.5)*24*c-(ty+.5)*24*s-ox
                y = (tx+.5)*24*s+(ty+.5)*24*c-oy
                target.blit(tile,(round(x-tile.get_width()/2),round(y-tile.get_height()/2)))

    def paint(self, target, key, painter, origin, angle=0):
        overlay = pygame.Surface((CHUNK,CHUNK),pygame.SRCALPHA)
        self.pattern(overlay,key,origin,angle)
        mask = pygame.Surface((CHUNK,CHUNK),pygame.SRCALPHA)
        painter(mask)
        overlay.blit(mask,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
        target.blit(overlay,(0,0))

    def polygon(self, target, feature, key, cx, cy, roughness=4, angle=0, inset=0):
        origin = (cx*CHUNK,cy*CHUNK)
        points = [self.world._tile_point(p) for p in feature['polygon']]
        if not self.world._feature_intersects(feature['polygon'],pygame.Rect(origin,(CHUNK,CHUNK)),roughness+8):return
        local = [(round(x-origin[0]),round(y-origin[1])) for x,y in points]
        area = sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1]))
        inward = 1 if area > 0 else -1
        def mask(surface):
            pygame.draw.polygon(surface,'white',local)
            if inset:self.world._draw_path(surface,(0,0,0,0),local+local[:1],inset*2)
            if roughness:
                closed = points+[points[0]]
                # Break the mathematical edge with small material stamps.
                # Samples are globally phased, keeping neighbouring chunks exact.
                for point,normal,index,segment in samples(closed,6,pygame.Rect(origin,(CHUNK,CHUNK)),24):
                    seed = stable(index,segment,37)
                    jitter = ((seed%(roughness*2+1))-roughness)+inset*inward
                    x = round(point[0]+normal[0]*jitter-origin[0]);y = round(point[1]+normal[1]*jitter-origin[1])
                    radius = 2+seed%max(2,roughness)
                    pygame.draw.circle(surface,'white',(x,y),radius)
        self.paint(target,key,mask,origin,angle)

    def ground(self, target, cx, cy):
        self.world._pattern(target,self.key('grass_meadow','grass'))
        terrain = self.world.region.get('terrain',{})
        for feature in terrain.get('hills',[]):
            if feature.get('ground_treatment') == 'localized':continue
            key = 'grass_dry' if feature.get('style') == 'rocky_ridge' else 'grass_lush'
            self.polygon(target,feature,self.key(key,'grass'),cx,cy,6)
        for feature in terrain.get('forests',[]):
            self.polygon(target,feature,self.key('grass_lush','forest_floor'),cx,cy,10)
        self._canopy_ground(target,cx,cy)
        crops = {'grain':'grain','vegetables':'vegetables','fallow':'furrows','pasture':'pasture','orchard':'orchard_grass'}
        for feature in terrain.get('fields',[]):
            key = self.key(crops.get(feature.get('crop'),'grain'),'field')
            self.polygon(target,feature,key,cx,cy,2,feature.get('row_angle',0))
        self._ridge_ground(target,cx,cy)
        for feature in terrain.get('shore_conditions',[]):
            key = {'gravel':'gravel','rocky':'gravel','damp':'leaf_litter',
                   'reeds':'grass_lush'}.get(feature.get('kind'),'grass_lush')
            self.polygon(target,feature,self.key(key,'bank'),cx,cy,5)
        for feature in terrain.get('yards',[]):
            self.polygon(target,feature,self.key(feature.get('surface','gravel'),'dirt'),cx,cy,4)
        for feature in terrain.get('scorched',[]):
            self.polygon(target,feature,'scorched',cx,cy,4)

    def _nearby_ground_props(self, cx, cy):
        view = pygame.Rect(cx*CHUNK,cy*CHUNK,CHUNK,CHUNK).inflate(160,100)
        for nx in range(cx-1,cx+2):
            for ny in range(cy-1,cy+2):
                metadata = self.world._chunk_metadata(nx,ny)
                if metadata:
                    for prop in metadata['props']:
                        if view.collidepoint(prop['position']):yield prop

    def _canopy_ground(self, target, cx, cy):
        """Fallen leaves collect beneath crowns, not across an entire biome."""
        origin = (cx*CHUNK,cy*CHUNK)
        view = pygame.Rect(origin,(CHUNK,CHUNK))
        forests = self.world.region.get('terrain',{}).get('forests',[])
        if not any(self.world._feature_intersects(f['polygon'],view,80) for f in forests):return
        crowns = [p for p in self._nearby_ground_props(cx,cy) if p.get('crown_ground')]
        if not crowns:return
        def mask(surface):
            for prop in crowns:
                x,y = prop['position'];seed = stable(round(x),round(y),251)
                width,height = 32+seed%16,18+(seed>>7)%10
                rect = pygame.Rect(round(x)-width//2-origin[0],
                                   round(y)-height//2-origin[1]-2,width,height)
                pygame.draw.ellipse(surface,'white',rect)
                for side in (-1,1):
                    pygame.draw.circle(surface,'white',
                                       (rect.centerx+side*(width//3),rect.centery+side*3),5)
        self.paint(target,self.key('leaf_litter','forest_floor'),mask,origin)

    def _ridge_ground(self, target, cx, cy):
        """Exposed earth hugs the authored rock shelf instead of a tan mat."""
        hills = [h for h in self.world.region.get('terrain',{}).get('hills',[])
                 if h.get('ground_treatment') == 'localized']
        if not hills:return
        origin = (cx*CHUNK,cy*CHUNK)
        view = pygame.Rect(origin,(CHUNK,CHUNK))
        if not any(self.world._feature_intersects(h['polygon'],view,80) for h in hills):return
        rocks = [p for p in self._nearby_ground_props(cx,cy)
                 if p.get('key') in ('ridge','rock_outcrop') and
                 any(inside((p['position'][0]/TILE,p['position'][1]/TILE),h['polygon'])
                     for h in hills)]
        if not rocks:return
        def mask(surface):
            for prop in rocks:
                x,y = prop['position'];wide = prop['key'] == 'ridge'
                width,height = (100,26) if wide else (64,20)
                rect = pygame.Rect(round(x)-width//2-origin[0],round(y)-height//2-origin[1],width,height)
                pygame.draw.ellipse(surface,'white',rect)
        self.paint(target,self.key('grass_dry','dirt'),mask,origin)

    @staticmethod
    def offset(points, distance):
        result = []
        for index,point in enumerate(points):
            a = points[max(0,index-1)];b = points[min(len(points)-1,index+1)]
            dx,dy = b[0]-a[0],b[1]-a[1];length = math.hypot(dx,dy) or 1
            result.append((point[0]-dy/length*distance,point[1]+dx/length*distance))
        return result

    def roads(self, target, cx, cy):
        origin = (cx*CHUNK,cy*CHUNK);viewport = pygame.Rect(origin,(CHUNK,CHUNK))
        roads = sorted(self.world.region.get('roads',[]),key=lambda r:{'foot':0,'cart':1,'stone':2}.get(r.get('kind'),1))
        for road in roads:
            width = road.get('width',3)*TILE
            if not self.world._feature_intersects(road['points'],viewport,width/2+20):continue
            points = self.world._local_path(road,cx,cy)
            global_points = [self.world._tile_point(p) for p in road['points']]
            kind = road.get('kind','stone' if road.get('surface') == 'stone_road' else 'cart')
            def draw_mask(surface,points=points,width=width):
                self.world._draw_path(surface,'white',points,width)
                for point,normal,index,segment in samples(global_points,11,viewport,width/2+16):
                    seed = stable(index,segment,81)
                    for side in (-1,1):
                        edge = width/2-1+seed%3
                        x = round(point[0]+normal[0]*edge*side-origin[0])
                        y = round(point[1]+normal[1]*edge*side-origin[1])
                        pygame.draw.circle(surface,(0,0,0,0),(x,y),1+seed%3)
            self.paint(target,self.key('grass_dry','dirt'),
                       lambda mask,p=points,w=width:self.world._draw_path(mask,'white',p,w+10),origin)
            if kind == 'cart' and road.get('ruts',True):
                # Connected wheel tracks, with a grassy center, distinguish cart
                # travel from paved routes and the narrower walking paths.
                self.paint(target,self.key('cart_earth','dirt'),draw_mask,origin)
                self.paint(target,self.key('grass_meadow','grass'),
                           lambda mask,p=points,w=width:self.world._draw_path(mask,'white',p,max(3,w*.26)),origin)
                for side in (-1,1):
                    rut = self.offset(points,width*.29*side)
                    self.paint(target,self.key('cart_earth','dirt'),
                               lambda mask,p=rut,w=width:self.world._draw_path(mask,'white',p,max(5,w*.2)),origin)
            else:
                key = self.key('stone_road_worn','stone_road') if kind == 'stone' else self.key('cart_earth','dirt')
                self.paint(target,key,draw_mask,origin)

    def bank(self, target, river, cx, cy):
        """Variable dry shore outside the unchanged, solid water footprint."""
        origin = (cx*CHUNK,cy*CHUNK);viewport = pygame.Rect(origin,(CHUNK,CHUNK))
        points = self.world._local_path(river,cx,cy)
        global_points = [self.world._tile_point(p) for p in river['points']]
        width = river.get('width',8)*TILE
        def grass(mask):
            self.world._draw_path(mask,'white',points,width+29)
            for point,normal,index,_ in samples(global_points,13,viewport,width/2+45):
                seed = stable(index,57,42)
                for side in (-1,1):
                    distance = width/2+11+seed%8
                    pygame.draw.circle(mask,'white',(round(point[0]+normal[0]*distance*side-origin[0]),
                                                     round(point[1]+normal[1]*distance*side-origin[1])),4+seed%5)
        self.paint(target,self.key('grass_lush','grass'),grass,origin)
        def earth(mask):
            self.world._draw_path(mask,'white',points,width+10)
            for point,normal,index,_ in samples(global_points,15,viewport,width/2+30):
                seed = stable(index,63,43)
                for side in (-1,1):
                    distance = width/2+3+seed%5
                    center = (round(point[0]+normal[0]*distance*side-origin[0]),
                              round(point[1]+normal[1]*distance*side-origin[1]))
                    pygame.draw.circle(mask,'white',center,3+seed%4)
        self.paint(target,'bank',earth,origin)
        def gravel(mask):
            for point,normal,index,_ in samples(global_points,47,viewport,width/2+35):
                seed = stable(index,61,44)
                if seed%3 == 0:continue
                side = -1 if seed%2 else 1
                distance = width/2+6
                center = (round(point[0]+normal[0]*distance*side-origin[0]),
                          round(point[1]+normal[1]*distance*side-origin[1]))
                pygame.draw.circle(mask,'white',center,4+seed%9)
        if not self.world.region.get('terrain',{}).get('shore_conditions'):
            self.paint(target,self.key('gravel','bank'),gravel,origin)

    def prop_frame(self, prop, elapsed_ms):
        animation = prop.get('animation') or {}
        frames = animation.get('frames',[])
        phase = stable(round(prop['position'][0]),round(prop['position'][1]),11)%1000
        key = prop['key']
        if frames:
            available = [frame for frame in frames if frame in self.world._art.get('props',{})]
            if available:key = available[int((elapsed_ms+phase)//max(80,animation.get('frame_ms',400)))%len(available)]
        x,y = prop['position'];motion = prop.get('motion')
        amplitude = min(6,max(0,float(prop.get('amplitude',2))))
        t = (elapsed_ms+phase)/1000
        if motion in ('flutter','bird'):
            x += round(math.sin(t*2.8)*amplitude);y += round(math.cos(t*3.4)*amplitude)
        elif motion == 'smoke':y -= round((t%2)/2*amplitude)
        elif motion == 'graze':x += round(math.sin(t*.5)*min(amplitude,1))
        return key,(x,y)
