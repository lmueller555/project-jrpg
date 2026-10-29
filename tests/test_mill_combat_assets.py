"""MQ02 combat sprites retain complete poses, provenance and impact timing."""
import hashlib
import json
import os
from pathlib import Path
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
from PIL import Image

from battle_model import load_actions
from battle_scene import CombatSprites


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT/'assets/combat'


def manifest(actor):
    return json.loads((ART/actor/'animation.json').read_text())


class MillCombatAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.display.set_mode((480, 320))
        cls.sprites = CombatSprites()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def assert_complete_actor(self, actor, canvas, anchor, facing, required):
        data = manifest(actor)
        self.assertEqual(data['canvas'], list(canvas))
        self.assertEqual(data['anchor'], list(anchor))
        self.assertEqual(data['facing'], facing)
        self.assertLessEqual(required, set(data['animations']))
        frames = {}
        for state, animation in data['animations'].items():
            self.assertIsInstance(animation['loop'], bool)
            self.assertGreaterEqual(len(animation['frames']), 2)
            for record in animation['frames']:
                self.assertGreater(record['duration_ms'], 0)
                frames[record['file']] = record
        self.assertEqual(len(frames), 16)
        images = []
        for filename in frames:
            with self.subTest(actor=actor, frame=filename):
                with Image.open(ART/actor/filename) as source:
                    image = source.convert('RGBA')
                self.assertEqual(image.size, canvas)
                alpha = image.getchannel('A')
                self.assertEqual(set(alpha.tobytes()), {0, 255})
                bounds = alpha.getbbox()
                self.assertIsNotNone(bounds)
                self.assertGreater(bounds[0], 0)
                self.assertGreater(bounds[1], 0)
                self.assertLess(bounds[2], canvas[0])
                self.assertLess(bounds[3], canvas[1])
                images.append(image.tobytes())
        self.assertEqual(len(set(images)), 16)

    def test_mira_has_complete_unclipped_native_spear_and_recovery_poses(self):
        self.assert_complete_actor('mira', (64, 64), (32, 54), 'left',
                                   {'idle', 'attack', 'guard', 'hurt', 'victory',
                                    'defeat', 'walk', 'spear_thrust', 'flee'})

    def test_tusker_has_distinct_native_preparation_charge_and_collapse_poses(self):
        self.assert_complete_actor('ridgeback_tusker', (96, 72), (48, 62), 'right',
                                   {'idle', 'attack', 'prepare', 'charge', 'hurt',
                                    'defeat', 'tusk_strike', 'prepare_charge',
                                    'tusker_charge'})

    def test_every_authored_pose_references_its_retained_source_atlas(self):
        for actor in ('mira', 'ridgeback_tusker'):
            with self.subTest(actor=actor):
                data = manifest(actor)
                source = ROOT/data['source_sheet']
                self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),
                                 data['source_sha256'])
                with Image.open(source) as image:
                    width, height = image.size
                records = {record['source_cell']: record
                           for state in data['animations'].values()
                           for record in state['frames']}
                self.assertEqual(set(records), set(range(16)))
                for record in records.values():
                    left, top, right, bottom = record['source_bounds']
                    self.assertTrue(0 <= left < right <= width)
                    self.assertTrue(0 <= top < bottom <= height)

    def test_spear_strike_and_charge_resolve_during_the_authored_contact_frame(self):
        actions = load_actions()
        for actor, state, action in (('mira', 'attack', 'spear_thrust'),
                                     ('ridgeback_tusker', 'attack', 'tusk_strike'),
                                     ('ridgeback_tusker', 'charge', 'tusker_charge')):
            with self.subTest(actor=actor, action=action):
                frames = manifest(actor)['animations'][state]['frames']
                self.assertEqual(len(frames), 3)
                self.assertEqual(sum(frame['duration_ms'] for frame in frames),
                                 round(actions[action]['duration']*1000))
                impact = actions[action]['impact_at']*1000
                self.assertLessEqual(frames[0]['duration_ms'], impact)
                self.assertLess(impact, frames[0]['duration_ms']+frames[1]['duration_ms'])
                actual, anchor = self.sprites.frame(actor, action, impact)
                expected = pygame.image.load(str(ART/actor/frames[1]['file']))
                self.assertEqual(pygame.image.tobytes(actual, 'RGBA'),
                                 pygame.image.tobytes(expected, 'RGBA'))
                self.assertEqual(anchor, tuple(manifest(actor)['anchor']))

    def test_charge_preparation_remains_visible_after_its_non_damaging_action(self):
        action = load_actions()['prepare_charge']
        animation = manifest('ridgeback_tusker')['animations']['prepare']
        duration = sum(frame['duration_ms'] for frame in animation['frames'])
        self.assertEqual(duration, round(action['duration']*1000))
        self.assertEqual(action['kind'], 'prepare')
        self.assertEqual(action['potency'], 0)
        self.assertTrue(animation['loop'])
        impact = action['impact_at']*1000
        self.assertLessEqual(animation['frames'][0]['duration_ms'], impact)
        self.assertLess(impact, duration)
        lowered, _ = self.sprites.frame('ridgeback_tusker', 'prepare', impact)
        expected = pygame.image.load(str(ART/'ridgeback_tusker'/
                                        animation['frames'][1]['file']))
        self.assertEqual(pygame.image.tobytes(lowered, 'RGBA'),
                         pygame.image.tobytes(expected, 'RGBA'))
        first, _ = self.sprites.frame('ridgeback_tusker', 'prepare', 0)
        after, _ = self.sprites.frame('ridgeback_tusker', 'prepare_charge', duration*3)
        self.assertEqual(pygame.image.tobytes(first, 'RGBA'),
                         pygame.image.tobytes(after, 'RGBA'))

    def test_overworld_spear_is_transparent_and_its_grip_tip_and_butt_are_registered(self):
        data = json.loads((ART/'mira/world_spear.json').read_text())
        with Image.open(ART/'mira/world_spear.png') as source:
            image = source.convert('RGBA')
        self.assertEqual(image.size, tuple(data['canvas']))
        self.assertEqual(image.size, (16, 48))
        self.assertEqual(data['orientation'], 'point_up')
        self.assertEqual(set(image.getchannel('A').tobytes()), {0, 255})
        bounds = image.getbbox()
        self.assertGreater(bounds[0], 0)
        self.assertGreater(bounds[1], 0)
        self.assertLess(bounds[2], image.width)
        self.assertLess(bounds[3], image.height)
        for point in (data['hand_anchor'], data['tip'], data['butt']):
            self.assertTrue(0 <= point[0] < image.width and 0 <= point[1] < image.height)
            self.assertEqual(image.getpixel(tuple(point))[3], 255)
        self.assertLess(data['tip'][1], data['hand_anchor'][1])
        self.assertLess(data['hand_anchor'][1], data['butt'][1])
        self.assertEqual(hashlib.sha256((ROOT/data['source']).read_bytes()).hexdigest(),
                         data['source_sha256'])

    def test_river_battlefield_has_native_opaque_canvas_and_verified_generated_source(self):
        folder = ART/'millrace'
        data = json.loads((folder/'scene.json').read_text())
        with Image.open(folder/data['background']) as image:
            self.assertEqual(image.size, (480, 320))
            self.assertEqual(list(image.size), data['canvas'])
            self.assertEqual(image.convert('RGBA').getchannel('A').getextrema(), (255, 255))
        source = ROOT/data['source']['file']
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),
                         data['source']['sha256'])
        with Image.open(source) as image:
            self.assertEqual(list(image.size), data['source']['dimensions'])
        self.assertEqual(data['world_map'], 'upstream')


if __name__ == '__main__':
    unittest.main()
