"""Native asset scenery occludes actual Caelan pixels at physical objects.

Depth probes are independently chosen from the assembled scene, rather than
inferred from exported sorting values. Ground provenance is checked against
the reusable source packs instead of retaining a background-painting hash.
"""
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from elden_vale_sanctuary import SanctuaryReserveWorld
from main import Player, camera_for

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT/'assets/maps/elden_vale_sanctuary/map.json'


class SanctuaryDepthTests(unittest.TestCase):
    def setUp(self):
        pygame.init();pygame.display.set_mode((480, 320))
        self.world = SanctuaryReserveWorld(MAP)
        self.player = Player(self.world)
        self.player.facing = 'front'

    def tearDown(self):pygame.quit()

    def assert_pixel_depth(self, feet, point, *, hidden):
        self.player.position.update(feet)
        self.assertTrue(self.world.can_stand(feet), ('Blocked test feet', feet))
        camera = camera_for(feet, self.world.size)
        before = pygame.Surface((480, 320))
        after = pygame.Surface((480, 320))
        invisible = SimpleNamespace(position=self.player.position, story_visible=False)
        self.world.draw(before, camera, invisible, 0)
        self.world.draw(after, camera, self.player, 0)
        local = (point[0]-feet[0]+12, point[1]-feet[1]+30)
        sprite_color = self.player.sprite().get_at(local)
        self.assertEqual(sprite_color.a, 255, ('Probe must hit an opaque Caelan pixel', local))
        screen = point[0]-camera[0], point[1]-camera[1]
        scenery = before.get_at(screen)
        self.assertNotEqual(scenery, sprite_color, 'The reference pixel must distinguish actor and scenery')
        self.assertEqual(after.get_at(screen), scenery if hidden else sprite_color,
                         ('Wrong scenery overlap', feet, point, 'hidden' if hidden else 'visible'))

    def test_ground_and_scenery_are_assembled_from_hash_verified_pixel_packs(self):
        manifest = json.loads((ROOT/'assets/terrain/elden_vale_sanctuary/art.json').read_text())
        sources = manifest['source_assets']
        paths = [record['path'] for record in sources]
        self.assertGreaterEqual(len(sources), 8)
        self.assertEqual(len(paths), len(set(paths)))
        for record in sources:
            with self.subTest(source=record['path']):
                self.assertEqual(hashlib.sha256((ROOT/record['path']).read_bytes()).hexdigest(),
                                 record['sha256'])
        self.assertTrue(any('/eldenmere/grass_dirt/' in path for path in paths))
        self.assertTrue(any('/eldenmere/foliage/' in path for path in paths))
        for obsolete in ('clean_plate_generated.png','approved_preview.png',
                         'elden_vale_cloister_openings','elden_vale_cave_barrier'):
            self.assertFalse(any(obsolete in path for path in paths),obsolete)
        self.assertEqual(self.world.data['build']['implementation'], 'native_pixel_asset_packs')
        self.assertEqual(self.world.data['build']['source_assets'], sources)
        self.assertNotIn('clean_plate_sha256', manifest)

    def test_western_tree_crown_covers_rear_poses_and_leaves_front_poses_visible(self):
        self.assert_pixel_depth((144,238),(144,218),hidden=True)
        self.assert_pixel_depth((144,310),(144,290),hidden=False)

    def test_open_grass_and_path_between_grove_objects_do_not_erase_the_character(self):
        for feet, point in (((600,400),(600,380)),((535,480),(535,460)),
                            ((240,400),(240,380))):
            with self.subTest(feet=feet):self.assert_pixel_depth(feet, point, hidden=False)

    def test_basin_and_bench_cover_rear_feet_and_leave_front_poses_visible(self):
        cases = (
            ('basin_back',(768,370),(764,364),True),
            ('basin_front',(768,412),(768,392),False),
            ('bench_back',(264,260),(262,256),True),
            ('bench_front',(264,300),(264,280),False),
        )
        for name, feet, point, hidden in cases:
            with self.subTest(name=name):self.assert_pixel_depth(feet, point, hidden=hidden)

    def test_cloister_front_pose_is_not_cut_by_its_rear_wall_or_the_hall_depth(self):
        for feet, point in (((699,317),(699,297)),((775,317),(775,297)),
                            ((851,317),(851,297))):
            with self.subTest(feet=feet):self.assert_pixel_depth(feet, point, hidden=False)

    def test_arch_stonework_covers_the_rear_pose_but_openings_stay_transparent(self):
        for name, feet, point, hidden in (
            ('arch_back', (444,600), (444,580), True),
            ('arch_opening', (444, 654), (444, 634), False),
            ('arch_front', (444, 711), (444, 691), False),
            ('hall_doorway', (535, 345), (535, 325), False),
        ):
            with self.subTest(name=name):self.assert_pixel_depth(feet, point, hidden=hidden)


if __name__ == '__main__':unittest.main()
