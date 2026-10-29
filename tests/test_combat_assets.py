"""Combat art is complete, unclipped and synchronized with action impacts."""
import hashlib
import json
import os
from pathlib import Path
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
from battle_model import load_actions
from battle_scene import CombatSprites


ROOT = Path(__file__).resolve().parents[1]


class CombatAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init();pygame.display.set_mode((480, 320))
        cls.sprites = CombatSprites()

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def test_all_combat_states_have_distinct_transparent_unclipped_native_frames(self):
        required = {'caelan': {'idle', 'attack', 'cast', 'guard', 'hurt', 'victory', 'defeat'},
                    'bat': {'idle', 'attack', 'cast', 'hurt', 'defeat'}}
        for actor, states in required.items():
            folder = ROOT/'assets/combat'/actor
            data = json.loads((folder/'animation.json').read_text())
            self.assertEqual(data['canvas'], [48, 48])
            self.assertEqual(data['anchor'], [24, 42])
            self.assertLessEqual(states, set(data['animations']))
            images = []
            for state in states:
                animation = data['animations'][state]
                self.assertGreaterEqual(len(animation['frames']), 2)
                self.assertIsInstance(animation['loop'], bool)
                for record in animation['frames']:
                    with self.subTest(actor=actor, state=state, frame=record['file']):
                        self.assertGreater(record['duration_ms'], 0)
                        image = pygame.image.load(str(folder/record['file']))
                        self.assertEqual(image.get_size(), (48, 48))
                        bounds = image.get_bounding_rect()
                        self.assertGreater(bounds.width*bounds.height, 0)
                        self.assertGreater(bounds.left, 0)
                        self.assertGreater(bounds.top, 0)
                        self.assertLess(bounds.right, 48)
                        self.assertLess(bounds.bottom, 48)
                        self.assertEqual({image.get_at((x, y)).a
                                          for y in range(48) for x in range(48)}, {0, 255})
                        images.append(pygame.image.tobytes(image, 'RGBA'))
            self.assertEqual(len(images), 16)
            self.assertEqual(len(set(images)), 16)

    def test_native_exports_reference_their_retained_generated_source_art(self):
        for actor in ('caelan', 'bat'):
            data = json.loads((ROOT/'assets/combat'/actor/'animation.json').read_text())
            path = ROOT/data['source_sheet']
            self.assertTrue(path.is_file())
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), data['source_sha256'])

    def test_attack_and_cast_impacts_use_contact_frames_before_recovery(self):
        actions = load_actions()
        for actor, action, state in (('caelan', 'attack', 'attack'),
                                     ('caelan', 'aether_dart', 'cast'),
                                     ('bat', 'bite', 'attack'),
                                     ('bat', 'wing_gust', 'cast')):
            with self.subTest(actor=actor, action=action):
                folder = ROOT/'assets/combat'/actor
                data = json.loads((folder/'animation.json').read_text())
                frames = data['animations'][state]['frames']
                self.assertEqual(sum(frame['duration_ms'] for frame in frames),
                                 round(actions[action]['duration']*1000))
                contact_start = frames[0]['duration_ms']
                contact_end = contact_start+frames[1]['duration_ms']
                impact = actions[action]['impact_at']*1000
                self.assertLessEqual(contact_start, impact)
                self.assertLess(impact, contact_end)
                actual, _ = self.sprites.frame(actor, state, impact)
                expected = pygame.image.load(str(folder/frames[1]['file']))
                self.assertEqual(pygame.image.tobytes(actual, 'RGBA'),
                                 pygame.image.tobytes(expected, 'RGBA'))


if __name__ == '__main__':unittest.main()
