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
        cls.art=json.loads((ROOT/'assets/terrain/elden_vale_sanctuary/art.json').read_text())
        cls.pack=json.loads((ROOT/'assets/terrain/grass/assets.json').read_text())

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def test_actual_ground_uses_all_twelve_approved_materials(self):
        materials=self.art['ground_materials']
        expected=[path for record in self.pack['materials'].values() for path in record['tiles']]
        self.assertEqual(materials['manifest'],'assets/terrain/grass/assets.json')
        self.assertEqual(materials['tiles'],expected)
        self.assertEqual({index for row in materials['indices'] for index in row},set(range(12)))
        # Check shipped pixels, not only the metadata: each of the twelve
        # materials must survive as complete tiles somewhere in the ground.
        with Image.open(ROOT/self.art['ground']) as image:
            ground=image.convert('RGB')
        tiles=[Image.open(ROOT/path).convert('RGB').tobytes() for path in expected]
        visible=set()
        for row,indices in enumerate(materials['indices']):
            for col,index in enumerate(indices):
                crop=ground.crop((col*24,row*24,(col+1)*24,(row+1)*24))
                if crop.tobytes()==tiles[index]:visible.add(index)
        self.assertEqual(visible,set(range(12)))

    def test_live_grass_is_separate_from_the_cached_ground_and_static_objects(self):
        data=self.world.data
        self.assertEqual(data['grass']['manifest'],'assets/terrain/grass/assets.json')
        instances=data['grass']['instances']
        self.assertGreater(len(instances),60)
        self.assertEqual(len({instance['id'] for instance in instances}),len(instances))
        self.assertEqual({instance['variant'] for instance in instances},set(self.pack['tall_grass']['variants']))
        self.assertFalse(any('grass_flowers/grass_' in path
                             for entity in data['entities'] for path in entity['frames']))
        self.assertFalse(any('grass_flowers/grass_' in record['path']
                             for record in self.art['source_assets']))
        self.assertTrue(any(record['path']=='assets/terrain/grass/assets.json'
                            for record in self.art['source_assets']))

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
