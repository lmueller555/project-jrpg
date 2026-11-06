"""Scenery occludes actual Caelan pixels only where a visible object is ahead.

The probes below were selected from the approved painted scene and reachable
player feet. They deliberately do not consult exported masks or sort values:
the former broad grove cutout erased the open-ground probes, while missing
oak, basin and bench layers left the character painted over solid scenery.
"""
import hashlib
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

    def test_ground_art_is_retained_while_only_depth_layers_change(self):
        expected = {
            'assets/terrain/elden_vale_sanctuary/ground.png':
                '3476df0237132ddc29325a5135ca9414b3cb906cf3725e486d74b3a0abadbd9a',
            'assets/terrain/elden_vale_sanctuary_hall/ground.png':
                '1e2612e5e59b8c00763a0416e28a22c8dd5405368bc4e7631fdafaa30627c4c7',
        }
        for path, digest in expected.items():
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(), digest, path)

    def test_northwest_oak_crown_covers_the_character_on_the_rear_walking_path(self):
        self.assert_pixel_depth((348, 88), (348, 75), hidden=True)

    def test_open_grass_and_path_between_grove_objects_do_not_erase_the_character(self):
        for feet, point in (((300, 360), (300, 340)), ((310, 360), (310, 340)),
                            ((290, 372), (290, 352))):
            with self.subTest(feet=feet):self.assert_pixel_depth(feet, point, hidden=False)

    def test_basin_bench_and_planter_cover_rear_feet_and_leave_front_poses_visible(self):
        cases = (
            ('basin_back', (750, 318), (746, 321), True),
            ('basin_front', (750, 378), (750, 358), False),
            ('bench_back', (271, 260), (271, 255), True),
            ('bench_front', (271, 310), (271, 290), False),
            ('planter_back', (704, 340), (700, 343), True),
            ('planter_front', (704, 382), (704, 362), False),
        )
        for name, feet, point, hidden in cases:
            with self.subTest(name=name):self.assert_pixel_depth(feet, point, hidden=hidden)

    def test_cloister_front_pose_is_not_cut_by_its_rear_wall_or_the_hall_depth(self):
        for feet, point in (((660, 330), (660, 311)), ((676, 330), (676, 301))):
            with self.subTest(feet=feet):self.assert_pixel_depth(feet, point, hidden=False)

    def test_arch_stonework_covers_the_rear_pose_but_openings_stay_transparent(self):
        for name, feet, point, hidden in (
            ('arch_back', (444, 615), (444, 595), True),
            ('arch_opening', (444, 654), (444, 634), False),
            ('arch_front', (444, 711), (444, 691), False),
            ('hall_doorway', (535, 345), (535, 325), False),
        ):
            with self.subTest(name=name):self.assert_pixel_depth(feet, point, hidden=hidden)


if __name__ == '__main__':unittest.main()
