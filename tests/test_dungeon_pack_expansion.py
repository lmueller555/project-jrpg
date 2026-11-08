"""The complete dungeon pack must remain reusable, walkable and reviewable."""
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
import zipfile

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import numpy as np
from PIL import Image
import pygame

from main import Player, camera_for
from sanctuary_cave_world import SanctuaryCaveWorld
from tools.capture_dungeon_pack import SOURCES, CATALOG, approved_hashes

ROOT=Path(__file__).resolve().parents[1]
MAP=ROOT/'assets/maps/dungeon_pack_review/map.json'


def segment(world, first, last):
    count=max(1,math.ceil(math.dist(first,last)))
    return all(world.can_stand((first[0]+(last[0]-first[0])*i/count,
                                first[1]+(last[1]-first[1])*i/count))
               for i in range(count+1))


def components(mask):
    pending={tuple(point) for point in np.argwhere(mask)};result=[]
    while pending:
        point=pending.pop();queue=[point];points=[point]
        while queue:
            y,x=queue.pop()
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    other=y+dy,x+dx
                    if other in pending:
                        pending.remove(other);queue.append(other);points.append(other)
        ys,xs=zip(*points)
        result.append((min(xs),min(ys),max(xs)-min(xs)+1,max(ys)-min(ys)+1))
    return result


class DungeonPackExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init();pygame.display.set_mode((480,320))
        cls.world=SanctuaryCaveWorld(MAP);cls.player=Player(cls.world)
        cls.player.facing='front';cls.player.moving=False
        cls.manifests={key:json.loads((ROOT/path).read_text()) for key,path in SOURCES.items()}

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def render(self, clock, visible=True):
        actor=self.player if visible else SimpleNamespace(position=self.player.position,story_visible=False)
        image=pygame.Surface((480,320));camera=camera_for(self.player.position,self.world.size)
        self.world.draw(image,camera,actor,clock,False)
        return image

    def test_new_assets_scene_and_full_catalogue_rebuild_deterministically(self):
        builders=('build_dungeon_structure.py','build_dungeon_water.py','build_dungeon_geology.py',
                  'build_microcrystal_adapters.py','build_dungeon_review_scene.py','build_dungeon_pack_catalog.py')
        def check(builder):
            result=subprocess.run([sys.executable,'tools/'+builder,'--check'],cwd=ROOT,
                                  capture_output=True,text=True,timeout=180)
            return builder,result
        with ThreadPoolExecutor(max_workers=3) as pool:
            for builder,result in pool.map(check,builders):
                self.assertEqual(result.returncode,0,builder+'\n'+result.stdout+result.stderr)
        for source,manifest in self.manifests.items():
            for path,expected in manifest['inputs'].items():
                self.assertEqual(sha256((ROOT/path).read_bytes()).hexdigest(),expected,(source,path))
            for path,expected in manifest['artifacts'].items():
                self.assertEqual(sha256((ROOT/path).read_bytes()).hexdigest(),expected,(source,path))
            for name,module in manifest['modules'].items():
                for path in module['frames']:
                    with Image.open(ROOT/path) as image:self.assertEqual(image.size,tuple(module['size']),(source,name,path))
                for x,y,w,h in module.get('footprints',[]):
                    self.assertTrue(0<=x<x+w<=module['size'][0] and 0<=y<y+h<=module['size'][1],(source,name,'footprint'))

    def test_catalogue_shows_every_floor_and_module_exactly_once(self):
        catalog=json.loads(CATALOG.read_text());entries=catalog['entries']
        expected=[]
        for source,manifest in self.manifests.items():
            for name,module in manifest['modules'].items():expected.append((source,module['frames'][0]))
            for material,record in manifest.get('materials',{}).items():
                for path in record['tiles']:expected.append((source,path))
        actual=[(entry['source'],entry['frames'][0]) for entry in entries.values()]
        self.assertEqual(Counter(actual),Counter(expected),'A variant is missing or duplicated in the full pack review')
        pages=catalog['pages'];keys=[key for page in pages for key in page['keys']]
        self.assertEqual(Counter(keys),Counter(entries.keys()),'Each entry needs one visible keyframe in the catalogue')
        for page in pages:
            self.assertTrue((ROOT/page['image']).is_file(),page)
            if page.get('animation'):self.assertTrue((ROOT/page['animation']).is_file())
        self.assertGreaterEqual(len(pages),6)
        for path,expected_hash in catalog.get('inputs',{}).items():
            self.assertEqual(sha256((ROOT/path).read_bytes()).hexdigest(),expected_hash,path)
        for path,expected_hash in catalog.get('artifacts',{}).items():
            self.assertEqual(sha256((ROOT/path).read_bytes()).hexdigest(),expected_hash,path)
        pdf=CATALOG.parent/'full_catalog.pdf'
        self.assertTrue(pdf.read_bytes().startswith(b'%PDF'))
        with zipfile.ZipFile(ROOT/catalog['archive']) as archive:
            self.assertEqual(sorted(archive.namelist()),sorted(catalog['archive_files']))
            for entry in entries.values():
                for path in entry['frames']:
                    self.assertIn(path,archive.namelist())
                    self.assertEqual(archive.read(path),(ROOT/path).read_bytes(),path)

    def test_directional_structure_and_passages_have_clear_native_openings(self):
        modules=self.manifests['structure']['modules']
        for direction in ('north','east','south','west'):
            for height in (24,48,72):self.assertIn(f'wall.face.{direction}.h{height}',modules)
            for kind in ('wall.cap','wall.base','ledge.edge','ramp','steps'):
                self.assertIn(kind+'.'+direction,modules)
            for width in ('narrow','wide'):
                module=modules[f'tunnel.{direction}.{width}']
                self.assertTrue(module.get('walkable_regions'),(direction,width))
                for region in module['walkable_regions']:
                    passage=pygame.Rect(region)
                    self.assertGreaterEqual(passage.width if direction in ('north','south') else passage.height,24,
                                            'A character footprint cannot fit the tunnel opening')
            self.assertIn('alcove.'+direction,modules)

    def test_water_animates_inside_fixed_banks_and_reusable_water_masks(self):
        modules=self.manifests['water']['modules'];animated=0;ports={}
        for name,module in modules.items():
            with self.subTest(water=name):
                frames=[]
                for path in module['frames']:
                    with Image.open(ROOT/path) as image:frames.append(np.array(image.convert('RGBA')))
                self.assertEqual(len(frames),1 if name.startswith('crust.') else 6)
                if any(not np.array_equal(frames[0],frame) for frame in frames[1:]):animated+=1
                if module.get('water_mask'):
                    with Image.open(ROOT/module['water_mask']) as image:mask=np.array(image.convert('L'))>0
                    declared=np.zeros(mask.shape,dtype=bool)
                    for x,y,w,h in module['water_regions']:declared[y:y+h,x:x+w]=True
                    self.assertTrue(np.array_equal(mask,declared),name+' water region mismatch')
                    for frame in frames[1:]:
                        self.assertTrue(np.array_equal(frame[~mask],frames[0][~mask]),name+' animated a bank')
                        self.assertTrue(np.array_equal(frame[:,:,3],frames[0][:,:,3]),name+' changed water geometry')
                    if name.startswith('stream.'):
                        edges={'north':mask[0,:],'east':mask[:,-1],
                               'south':mask[-1,:],'west':mask[:,0]}
                        for direction,edge in edges.items():
                            if direction in module['connections']:
                                self.assertGreaterEqual(np.count_nonzero(edge),8,
                                                        name+' has a pinched or sealed '+direction+' stream port')
                                axis='vertical' if direction in ('north','south') else 'horizontal'
                                if axis in ports:self.assertTrue(np.array_equal(edge,ports[axis]),
                                                                name+' cannot join its adjacent stream tile')
                                else:ports[axis]=edge
                            else:self.assertFalse(np.any(edge),name+' leaks water through a closed edge')
                else:self.assertEqual(module.get('collision_kind'),'none')
        self.assertGreater(animated,len(modules)//2)

    def test_new_microcrystal_orientations_preserve_tiny_separate_facets(self):
        modules=self.manifests['micro_adapters']['modules'];colors=set();patterns=set()
        for name,module in modules.items():
            with self.subTest(seam=name):
                colors.add(module['gem_color']);patterns.add(module['pattern'])
                frames=[]
                for path in module['frames']:
                    with Image.open(ROOT/path) as image:frames.append(np.array(image.convert('RGBA')))
                self.assertEqual(len(frames),6);alpha=frames[0][:,:,3]
                for frame in frames[1:]:self.assertTrue(np.array_equal(alpha,frame[:,:,3]))
                animated=np.any(np.stack([frame[:,:,:3]!=frames[0][:,:,:3] for frame in frames[1:]]),axis=(0,3))&(alpha>0)
                found=components(animated)
                self.assertEqual(len(found),module['crystal_count'])
                for x,y,w,h in found:
                    self.assertLessEqual(w,4);self.assertLessEqual(h,5)
                self.assertGreater(frames[-1][:,:,:3][animated].mean(),frames[0][:,:,:3][animated].mean()+5)
                self.assertFalse(module['footprints'])
        self.assertEqual(colors,{'red','blue','green','white','orange','purple'})
        self.assertTrue({'vertical','diagonal_left','diagonal_right','corner_inner','corner_outer','sparse','dense'}<=patterns)

    def test_full_foot_routes_reach_every_station_and_cross_the_ramp(self):
        world=self.world;spawn=tuple(world.data['spawn']);start=tuple(round(value/6)*6 for value in spawn)
        self.assertTrue(segment(world,spawn,start));seen={start};queue=deque([start])
        while queue:
            first=queue.popleft()
            for dx,dy in ((6,0),(-6,0),(0,6),(0,-6)):
                last=first[0]+dx,first[1]+dy
                if last in seen or not(0<=last[0]<world.size[0] and 0<=last[1]<world.size[1]):continue
                if segment(world,first,last):seen.add(last);queue.append(last)
        cave=world.data['cave'];self.assertGreaterEqual(len(cave['review_points']),14)
        targets=list(cave['review_points'].values())+[point for route in cave['routes'].values() for point in route]
        for point in targets:
            with self.subTest(point=point):
                self.assertTrue(world.can_stand(point))
                self.assertTrue(any(math.dist(other,point)<=9 and segment(world,other,point) for other in seen),
                                'A station is only reachable by a collision jump')
        checks=cave['review_checks']
        for record in checks['solid_points']:self.assertFalse(world.can_stand(record['position']),record)
        ramp=checks['ramp_checks']
        for first,last in zip((ramp['lower'],ramp['middle']),(ramp['middle'],ramp['upper'])):
            self.assertTrue(segment(world,first,last),'A ramp is blocked by its own raised shelf')

    def test_lighting_actor_depth_and_reduced_motion_use_the_production_renderer(self):
        world=self.world;checks=world.data['cave']['review_checks'];world.reduced_motion=False
        self.player.position.update(checks['light_station'])
        frames=[self.render(clock) for clock in (0,1000,2000,3000,4000,5000)]
        arrays=np.array([pygame.surfarray.array3d(image) for image in frames],dtype=np.int16)
        camera=camera_for(self.player.position,world.size);floor_pixels=[]
        for x in range(8,472,12):
            for y in range(8,312,12):
                point=x+camera[0],y+camera[1]
                if (world.can_stand(point) and math.dist(point,self.player.position)>24
                        and not any(entity['rect'].collidepoint(point) for entity in world.entities)):
                    floor_pixels.append((x,y))
        self.assertGreater(len(floor_pixels),10)
        change=np.ptp(arrays,axis=0).sum(axis=2)
        self.assertGreater(np.percentile([change[x,y] for x,y in floor_pixels],80),5,
                           'Animated water or sparkling mineral alone cannot prove environmental light')
        darkest=int(np.argmin(arrays.mean(axis=(1,2,3))))
        bare=self.render(darkest*1000,False)
        self.assertGreater(np.any(pygame.surfarray.array3d(frames[darkest])!=pygame.surfarray.array3d(bare),axis=2).sum(),80)
        world.reduced_motion=True
        self.assertTrue(checks.get('depth_cases'),'The scene needs a measured foreground depth review')
        for case in checks.get('depth_cases',[]):
            for feet,pixel,hidden in (('feet','hidden_pixel',True),('visible_feet','visible_pixel',False)):
                self.player.position.update(case[feet]);self.assertTrue(world.can_stand(self.player.position))
                shown,bare=self.render(0),self.render(0,False);camera=camera_for(self.player.position,world.size)
                x,y=case[pixel];screen=round(x-camera[0]),round(y-camera[1])
                self.assertEqual(shown.get_at(screen)==bare.get_at(screen),hidden)
        self.player.position.update(checks['light_station'])
        self.assertEqual(pygame.image.tobytes(self.render(0),'RGB'),pygame.image.tobytes(self.render(19321),'RGB'))
        world.reduced_motion=False

    def test_retained_review_and_approved_files_remain_intact(self):
        from tools.capture_dungeon_pack import OUT, check
        self.assertTrue(approved_hashes());check(OUT)
        report=json.loads((OUT/'verification.json').read_text())
        names={record['name'] for record in report['stations']}
        self.assertTrue(set(self.world.data['cave']['review_points'])<=names)
        self.assertLessEqual(report.get('movie_seconds',100),100)


if __name__=='__main__':unittest.main()
