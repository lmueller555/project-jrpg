"""Authored cave geometry must support full-foot travel and honest scenery."""
import json
import os
from pathlib import Path
import subprocess
import sys
from collections import deque
import unittest
from PIL import Image
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from main import World
ROOT=Path(__file__).resolve().parents[1]


class CaveAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init();pygame.display.set_mode((1,1))
        cls.worlds={key:World(ROOT/f'assets/maps/sanctuary_cave/{key}/map.json') for key in ('entrance','hollow','depths')}

    def test_deterministic_assets_and_reusable_modules(self):
        result=subprocess.run([sys.executable,'tools/build_sanctuary_cave.py','--check'],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        manifest=json.loads((ROOT/'assets/terrain/sanctuary_cave/assets.json').read_text())
        self.assertGreaterEqual(len(manifest['modules']),60)
        for family in ('wall.face.','wall.return_left.','wall.return_right.','wall.overhang.','stalagmites.','stalactites.'):
            self.assertTrue(any(key.startswith(family) for key in manifest['modules']),family)
        from hashlib import sha256
        for path,digest in manifest['artifacts'].items():self.assertEqual(sha256((ROOT/path).read_bytes()).hexdigest(),digest,path)

    def test_full_foot_reachability_of_links_rewards_routes_and_review_positions(self):
        for key,world in self.worlds.items():
            with self.subTest(scene=key):
                start=tuple(round(n/6)*6 for n in world.data['spawn']);self.assertTrue(world.can_stand(start))
                seen={start};queue=deque([start])
                while queue:
                    x,y=queue.popleft()
                    for point in ((x+6,y),(x-6,y),(x,y+6),(x,y-6)):
                        if point in seen or not (0<=point[0]<world.size[0] and 0<=point[1]<world.size[1]):continue
                        if world.can_stand(point):seen.add(point);queue.append(point)
                cave=world.data['cave'];targets=[world.data['spawn']]
                targets += [r['approach'] for r in cave['treasures']]
                targets += [r['position'] for r in cave['links']]
                targets += list(cave['review_points'].values())
                targets += [point for route in cave['routes'].values() for point in route]
                for target in targets:
                    self.assertTrue(world.can_stand(target),(key,target))
                    self.assertTrue(any(abs(x-target[0])<=6 and abs(y-target[1])<=6 for x,y in seen),(key,target,'disconnected'))
                for link in cave['links']:
                    visual=next((entity for entity in world.data['entities'] if entity.get('link_id')==link['id']),None)
                    self.assertIsNotNone(visual,(key,link['id'],'missing visible passage'))
                    self.assertEqual(visual['kind'],'tunnel_mouth')
                    self.assertIn('/tunnels/mouth_',visual['frames'][0])
                    if link['destination']=='elden_vale_sanctuary':continue
                    destination=self.worlds[link['destination'].removeprefix('sanctuary_cave_')]
                    self.assertTrue(destination.can_stand(link['landing']),(key,link))

    def test_treasure_states_have_solid_bases_and_identical_dimensions(self):
        identifiers=set()
        for world in self.worlds.values():
            for treasure in world.data['cave']['treasures']:
                self.assertNotIn(treasure['id'],identifiers);identifiers.add(treasure['id'])
                entity=next(e for e in world.data['entities'] if e['id']==treasure['entity_id'])
                self.assertEqual(set(entity['state_images']),{'closed','open'})
                sizes=[Image.open(ROOT/path).size for path in entity['state_images'].values()]
                self.assertEqual(sizes[0],sizes[1])
                x,y,w,h=entity['footprint']
                self.assertFalse(world.can_stand((x+w/2,y+h/2)))
        self.assertEqual(len(identifiers),6)

    def test_water_and_map_edges_are_solid_and_lighting_is_authored(self):
        for key,world in self.worlds.items():
            self.assertFalse(world.can_stand((12,12)))
            self.assertFalse(world.can_stand((world.size[0]-12,world.size[1]-12)))
            for entity in world.data['entities']:
                if entity['id'].startswith('pool_reflection'):
                    x,y=entity['position'];w,h=Image.open(ROOT/entity['frames'][0]).size
                    self.assertFalse(world.can_stand((x+w//2,y+h//2)),key)
                    self.assertGreater(len(entity['frames']),1)
                if entity['id'].startswith(('crystal_','wall_vein_')):
                    self.assertIn('light_index',entity)
                    self.assertLess(entity['light_index'],len(world.data['cave']['lights']))
            for light in world.data['cave']['lights']:
                self.assertEqual(world.blocked.get_at(tuple(light['position'])),0,(key,light))

if __name__=='__main__':unittest.main()
