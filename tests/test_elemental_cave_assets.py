"""Two optional continuous rooms, honest Aqua spacing and dedicated battle stages."""
from collections import deque
from hashlib import sha256
import heapq
import json
import math
import os
from pathlib import Path
import unittest

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import numpy as np
from PIL import Image, ImageDraw
import pygame

from cave_battlefield import CaveBattlefield
from cave_random_encounters import CaveRandomEncounters, BATTLEFIELDS
from main import World

ROOT=Path(__file__).resolve().parents[1]
MAP=ROOT/'assets/maps/sanctuary_cave/map.json'
ROOMS={'embravyr':'embervein_chamber','nivareth':'stillfrost_chamber'}
FIELDS={'embravyr':'cave_embervein','nivareth':'cave_stillfrost'}


def raster_safe(data, config, *, branch=None):
    mask=Image.new('L',tuple(data['size_pixels']));draw=ImageDraw.Draw(mask)
    for poly in config['safe_polygons'].values():
        if branch is None:draw.polygon([tuple(p) for p in poly],fill=255)
    for room in data['cave']['rooms']:
        if config['rooms'][room['id']]['area'] is None and (branch is None or room['id']==branch.replace('_branch','_chamber')):
            draw.polygon([tuple(p) for p in room['polygon']],fill=255)
    for name,route in config['routes'].items():
        if branch is not None and name!=branch:continue
        radius=route['width']//2
        for band in route['bands']:
            if band['area'] is not None:continue
            points=[tuple(p) for p in data['cave']['routes'][name][band['first']:band['last']+2]]
            draw.line(points,fill=255,width=route['width'])
            for x,y in points:draw.ellipse((x-radius,y-radius,x+radius,y+radius),fill=255)
    return np.asarray(mask)>0


def probe_grid(collision):
    height,width=collision.shape
    integral=np.pad(collision.astype(np.int32).cumsum(0).cumsum(1),((1,0),(1,0)))
    xs=np.arange(12,width-12,4);ys=np.arange(8,height-8,4)
    x,y=np.meshgrid(xs,ys)
    blocked=integral[y+6,x+12]-integral[y-6,x+12]-integral[y+6,x-12]+integral[y-6,x-12]
    return xs,ys,x,y,blocked==0


class ElementalCaveAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init();pygame.display.set_mode((1,1))
        cls.data=json.loads(MAP.read_text());cls.cave=cls.data['cave']
        cls.spec=json.loads((ROOT/cls.data['build']['source_recipe']).read_text())
        cls.config=json.loads((ROOT/'assets/combat/cave_encounters.json').read_text())
        cls.world=World(MAP)
        cls.collision=np.asarray(Image.open(ROOT/cls.data['collision']).convert('L'))>0
        cls.arenas={arena['id']:arena for arena in cls.cave['elemental_arenas']}

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def test_two_rooms_preserve_existing_map_routes_landings_and_treasures(self):
        self.assertEqual(self.data['size_pixels'],[2400,1944])
        self.assertEqual(self.data['player_probe_size'],[24,12])
        self.assertEqual(set(self.arenas),set(ROOMS))
        self.assertEqual(self.cave['navigation_points']['entrance'],[288,1660])
        self.assertEqual(self.cave['navigation_points']['vein_gallery'],[456,1280])
        self.assertEqual(self.cave['navigation_points']['splitstone_hollow'],[1100,1200])
        self.assertEqual(self.cave['navigation_points']['echo_chamber'],[2060,300])
        self.assertEqual(self.cave['arena']['enemy_id'],'vespermaw')
        self.assertEqual(len(self.cave['links']),1)
        self.assertEqual(self.cave['links'][0]['destination'],'elden_vale_sanctuary')
        self.assertEqual({t['id']:t['position'] for t in self.cave['treasures']},{
            'cave_vein_cache':[334,1200],'cave_grotto_pack':[214,1003],
            'cave_grotto_chest':[562,750],'cave_keeper_chest':[1190,1650],
            'cave_overlook_cache':[1252,944],'cave_quiet_cache':[1710,570]})
        self.assertEqual(self.cave['routes']['main'],[[288,1660],[288,1510],[330,1400],
            [456,1280],[680,1270],[875,1240],[1100,1200],[1370,1180],[1510,1060],
            [1680,970],[1730,800],[1790,700],[1810,600],[1920,520],[2000,420],[2060,300]])
        for enemy,arena in self.arenas.items():
            self.assertEqual(arena['enemy_id'],enemy)
            self.assertEqual(arena['level'],4)
            self.assertEqual(arena['room'],ROOMS[enemy])
            self.assertEqual(arena['battlefield'],FIELDS[enemy])
            self.assertEqual(arena['status'],'story_boss')
            trigger=pygame.Rect(arena['trigger'])
            self.assertTrue(trigger.collidepoint(arena['center']))
            self.assertFalse(trigger.collidepoint(arena['approach']))
            for key in ('center','approach','retreat'):
                self.assertTrue(self.world.can_stand(arena[key]),(enemy,key))
            room=next(r for r in self.cave['rooms'] if r['id']==arena['room'])
            x,y=zip(*room['polygon'])
            self.assertEqual((max(x)-min(x),max(y)-min(y)),(336,288))

    def test_both_spurs_allow_full_foot_walk_and_leave_old_main_route_optional(self):
        source_corridors={r['id']:r for r in self.spec['corridors']}
        for name in ('embervein_branch','stillfrost_branch'):
            self.assertEqual(source_corridors[name]['width'],96)
            route=self.cave['routes'][name]
            self.assertEqual(route,source_corridors[name]['points'])
            for first,last in zip(route,route[1:]):
                distance=max(1,math.ceil(math.dist(first,last)))
                for step in range(distance+1):
                    point=[first[i]+(last[i]-first[i])*step/distance for i in (0,1)]
                    self.assertTrue(self.world.can_stand(point),(name,point))
        self.assertEqual(self.cave['routes']['embervein_branch'][0],[680,1270])
        self.assertEqual(self.cave['routes']['stillfrost_branch'][0],[1580,840])
        # The alternative reflecting loop reaches the main junction without
        # entering either new branch; no Fire prerequisite was added to it.
        self.assertEqual(self.cave['routes']['reflecting_loop'][0],[456,1280])
        self.assertEqual(self.cave['routes']['reflecting_loop'][-1],[1100,1200])
        self.assertEqual({loop['id'] for loop in self.cave['loops']},{'reflecting_grotto','keepers_recess'})

    def test_protected_foyers_pause_the_shared_counter_and_are_not_random_pools(self):
        counter=CaveRandomEncounters(seed=9)
        before=counter.to_dict()
        for arena in self.arenas.values():
            for key in ('center','approach','retreat'):
                region=counter.region_at(arena[key])
                self.assertIsNone(region['area'],(arena['id'],key,region))
                self.assertIsNone(counter.advance(1000,arena[key]))
                self.assertEqual(counter.remaining_distance,before['remaining'])
        self.assertEqual(counter.region_at([744,1392])['area'],'outer')
        self.assertEqual(counter.region_at([1580,840])['area'],'deep')
        self.assertFalse(set(FIELDS.values()) & BATTLEFIELDS)
        # A maximum-distance lesson ticket triggers before the first protected
        # foe room on the direct authored route, with exactly two level-two bats.
        counter=CaveRandomEncounters(seed=9)
        state=counter.to_dict();state['threshold']=state['remaining']=864
        self.assertTrue(counter.restore(state))
        path=self.cave['routes']['main'][:5]+self.cave['routes']['embervein_branch'][1:]
        ticket=None
        for first,last in zip(path,path[1:]):
            ticket=counter.travel(first,last,introductory=True)
            if ticket:break
        self.assertIsNotNone(ticket)
        self.assertEqual(ticket['lesson'],'aqua_edge')
        self.assertEqual(ticket['members'],[{'enemy_id':'cave_bat','level':2}]*2)
        self.assertIsNotNone(counter.region_at(ticket['position'])['area'])

    def test_shortest_probe_aware_eligible_route_exceeds_max_aqua_roll(self):
        # Count only dangerous travel on every reachable4px grid route, giving
        # safe rooms zero cost. Every node uses the real24x12 ground footprint.
        # This catches corner-cutting shortcuts that centerline sums miss.
        xs,ys,x,y,free=probe_grid(self.collision)
        safe=raster_safe(self.data,self.config)[y,x]
        distances=np.full(free.shape,np.inf);heap=[]
        for iy,ix in np.argwhere(free & safe & (x>=180)&(x<=410)&(y>=1608)&(y<=1810)):
            distances[iy,ix]=0.;heapq.heappush(heap,(0.,int(iy),int(ix)))
        steps=[(dy,dx,4*math.hypot(dx,dy)) for dy in (-1,0,1) for dx in (-1,0,1) if dx or dy]
        while heap:
            distance,iy,ix=heapq.heappop(heap)
            if distance>distances[iy,ix]+1e-9:continue
            for dy,dx,length in steps:
                ny,nx=iy+dy,ix+dx
                if not (0<=ny<len(ys) and 0<=nx<len(xs)) or not free[ny,nx]:continue
                if dx and dy and (not free[iy,nx] or not free[ny,ix]):continue
                cost=length*((not safe[iy,ix])+(not safe[ny,nx]))/2
                proposal=distance+cost
                if proposal+1e-9<distances[ny,nx]:
                    distances[ny,nx]=proposal;heapq.heappush(heap,(proposal,ny,nx))
        for branch in ('embervein_branch','stillfrost_branch'):
            goal=raster_safe(self.data,self.config,branch=branch)[y,x]
            minimum=np.min(np.where(free & goal,distances,np.inf))
            self.assertTrue(math.isfinite(minimum),branch)
            self.assertGreater(minimum,864+48,(branch,minimum))

    def test_room_crystals_are_dense_tiny_wall_embedded_and_bound_to32_lights(self):
        floor=Image.new('L',tuple(self.data['size_pixels']));draw=ImageDraw.Draw(floor)
        for room in self.spec['rooms']:draw.polygon([tuple(p) for p in room['polygon']],fill=255)
        for route in self.spec['corridors']:
            points=[tuple(p) for p in route['points']];radius=route['width']//2
            draw.line(points,fill=255,width=route['width'])
            for x,y in points:draw.ellipse((x-radius,y-radius,x+radius,y+radius),fill=255)
        floor=np.asarray(floor)>0
        pack=json.loads((ROOT/self.spec['manifests']['micro']).read_text())
        self.assertLessEqual(len(self.cave['lights']),32)
        for prefix,colors,minimum in [('embervein_',{'red','orange'},500),('stillfrost_',{'white','blue'},500)]:
            fields=[e for e in self.data['entities'] if e['id'].startswith(prefix) and 'light_index' in e]
            self.assertEqual({e['wall_gem_color'] for e in fields},colors)
            self.assertEqual({e['wall_side'] for e in fields if 'wall_side' in e},
                             {'north','south','east','west'})
            total=0
            for entity in fields:
                module=pack['modules'][entity['source_module']];total+=module['crystal_count']
                x,y=entity['position']
                for bx,by,width,height in module['core_components']:
                    self.assertLessEqual(width,4);self.assertLessEqual(height,5)
                    self.assertFalse(floor[y+by:y+by+height,x+bx:x+bx+width].any(),entity['id'])
            self.assertGreaterEqual(total,minimum)

    def test_dedicated_battlefields_are_cached_six_second_native_cycles(self):
        for enemy,identifier in FIELDS.items():
            with self.subTest(enemy=enemy):
                field=CaveBattlefield(identifier);data=field.data
                self.assertEqual(data['source_rooms'],[ROOMS[enemy]])
                self.assertEqual(data['source_position'],self.arenas[enemy]['center'])
                self.assertEqual(data['size'],[480,320]);self.assertEqual(len(field.frames),24)
                self.assertEqual(data['frame_duration_ms'],250)
                self.assertEqual(data['animation']['period_ms'],6000)
                self.assertEqual(set(data['animation']['crystal_colors']),{'red','orange'} if enemy=='embravyr' else {'white','blue'})
                self.assertGreaterEqual(data['animation']['microcrystal_count'],200)
                frames={pygame.image.tobytes(field.frame(i*250),'RGB') for i in range(24)}
                self.assertGreaterEqual(len(frames),20)
                self.assertIs(field.frame(0),field.frame(6000))
                self.assertIs(field.frame(1250,True),field.frames[8])
                for path,digest in data['build']['source_sha256'].items():
                    self.assertEqual(sha256((ROOT/path).read_bytes()).hexdigest(),digest,path)


if __name__=='__main__':unittest.main()
