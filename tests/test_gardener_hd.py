"""The sanctuary gardener's native-density look must not change her mechanics."""
import json
import os
from pathlib import Path
import random
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from main import Game
from npc_routines import GARDENER_HD_ACTION, Gardener
from rendering import WorldCanvas

ROOT = Path(__file__).resolve().parents[1]
LEGACY = 'assets/characters/npcs/female_02/gardener/animations.json'


class GardenerHDTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game = Game(fullscreen=False, start_on_title=False)
        cls.world = cls.game.town
        cls.record = next(a.data for a in cls.world.npcs if a.data['id'] == 'sanctuary_gardener')

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def actor(self):
        self.world.well.owner = None
        return Gardener(self.record, self.world, random.Random(23))

    def test_native_body_bank_changes_no_poses_grips_layering_or_cues(self):
        before = json.loads((ROOT / LEGACY).read_text())
        actor = self.actor()
        after = actor.animation
        self.assertEqual(actor.animation_path, GARDENER_HD_ACTION)
        self.assertIn('/adult_woman_02/', actor.portrait_path)
        for name in ('water_capacity', 'body_offset', 'draw_anchor', 'foot_anchor',
                     'action_canvas', 'animations', 'buckets'):
            self.assertEqual(before[name], after[name], name)
        self.assertEqual(set(before['poses']), set(after['poses']))
        for name, old in before['poses'].items():
            with self.subTest(pose=name):
                record = after['poses'][name]
                for key in ('grip', 'order'):
                    self.assertEqual(record[key], old[key])
                image = actor.bodies[name]
                self.assertIsInstance(image, WorldCanvas)
                self.assertEqual(image.get_size(), (48, 48))
                self.assertEqual(image.native.get_size(), (96, 96))
                self.assertGreater(image.native.get_bounding_rect().width, 14)
                self.assertEqual(set(pygame.image.tobytes(image.native, 'RGBA')[3::4]), {0, 255})
        self.assertEqual(actor.buckets.keys(), self.world.well.pails.keys())
        for name, bucket in actor.buckets.items():
            self.assertEqual(pygame.image.tobytes(bucket.native, 'RGBA'),
                             pygame.image.tobytes(self.world.well.pails[name].native, 'RGBA'))

    def test_walk_between_well_stations_uses_roster_not_a_second_pail(self):
        actor = self.actor()
        actor.step_index = next(i for i, s in enumerate(actor.steps) if s['id'] == 'well_to_crank')
        actor.facing = 'right'
        actor.moving = True
        actor.walk_ms = 350
        expected = WorldCanvas((48, 48), pygame.SRCALPHA)
        body = actor.roster_art.sprite('right', True, 350)
        expected.blit(body, actor.animation['body_offset'])
        current = actor.sprite(0)
        self.assertEqual(pygame.image.tobytes(current.native, 'RGBA'),
                         pygame.image.tobytes(expected.native, 'RGBA'))
        actor.walk_ms += 70
        self.assertNotEqual(pygame.image.tobytes(actor.sprite(0).native, 'RGBA'),
                            pygame.image.tobytes(expected.native, 'RGBA'))


if __name__ == '__main__':
    unittest.main()
