"""The live Sanctuary uses the approved terrain without covering public routes."""
import json
import os
from pathlib import Path
import unittest

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')

from PIL import Image
import pygame

from elden_vale_sanctuary import SanctuaryReserveWorld


ROOT=Path(__file__).resolve().parents[1]


class SanctuaryGrassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init();pygame.display.set_mode((480,320))
        cls.world=SanctuaryReserveWorld(ROOT/'assets/maps/elden_vale_sanctuary/map.json')
        cls.art=json.loads((ROOT/cls.world.data['art_bank']).read_text())
        cls.pack=json.loads((ROOT/'assets/terrain/eldenmere/grass_dirt_hd/tileset.json').read_text())

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def test_actual_ground_preserves_native_approved_grass_arrangements(self):
        ground=Image.new('RGBA',tuple(v*2 for v in self.world.size))
        for chunk in self.world.data['ground_overlays']:
            ground.alpha_composite(Image.open(ROOT/chunk['image']).convert('RGBA'),tuple(v*2 for v in chunk['position']))
        expected=[Image.open(ROOT/'assets/terrain/eldenmere/grass_dirt_hd'/path).convert('RGBA').tobytes() for path in self.pack['materials']['grass']]
        visible=set()
        for y in range(self.world.size[1]//24):
            for x in range(self.world.size[0]//24):
                tile=ground.crop((x*48,y*48,(x+1)*48,(y+1)*48)).tobytes()
                if tile in expected:visible.add(expected.index(tile))
        self.assertEqual(visible,set(range(len(expected))))

    def test_live_grass_is_separate_from_the_cached_ground_and_static_objects(self):
        data=self.world.data
        self.assertEqual(data['grass']['manifest'],'assets/maps/sanctuary_reserve_hd/grass.json')
        instances=data['grass']['instances']
        self.assertGreater(len(instances),60)
        self.assertEqual(len({instance['id'] for instance in instances}),len(instances))
        live=json.loads((ROOT/data['grass']['manifest']).read_text())
        self.assertEqual({instance['variant'] for instance in instances},set(live['tall_grass']['variants']))
        self.assertTrue(all(key.endswith('_hd') for key in live['tall_grass']['variants']))
        self.assertFalse(any('grass_flowers/grass_' in path
                             for entity in data['entities'] for path in entity['frames']))

    def test_grass_roots_are_walkable_and_stay_clear_of_public_gathering_points(self):
        data=self.world.data
        public=[data['spawn'],data['reserve_exit']['position'],
                *data['public_approaches'].values(),*data['loop_waypoints'],
                *[door['anchor'] for door in data['doors']]]
        for instance in data['grass']['instances']:
            with self.subTest(instance=instance['id']):
                position=pygame.Vector2(instance['position'])
                self.assertTrue(self.world.can_stand(position))
                self.assertGreater(min(position.distance_to(point) for point in public),34)


if __name__=='__main__':unittest.main()
