"""Authored action poses retain their body scale, clock and equipment identity."""
import hashlib
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame

from combat_motion_art import MOTION_STATES, anchors, frame, prepare_combat_motion_art
from gearblade_art import prepare_combat_art

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'assets/combat/caelan_motion'


class CombatMotionArtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((64, 64))
        cls.art = prepare_combat_motion_art()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_complete_equipped_and_unarmed_body_banks(self):
        expected = {'run': 6, 'plant': 3, 'slash': 2, 'followthrough': 2,
                    'retreat': 4, 'land': 2, 'cast_prepare': 4,
                    'cast_release': 1, 'cast_recover': 1, 'guard_enter': 3,
                    'guard_impact': 3, 'hurt_recover': 3}
        for family in ('armed', 'unarmed'):
            self.assertEqual(len(self.art.records[family]), 36)
            for state, count in expected.items():
                sequence = self.art.sequences[family][state]
                self.assertEqual(len(sequence), count, (family, state))
                self.assertEqual(len({pygame.image.tobytes(image, 'RGBA')
                                      for image, _, _ in sequence}), count)
            self.assertTrue(all(record['whole_body'] and record['facing'] == 'left'
                                for record in self.art.records[family]))

    def test_fixed_floor_and_blade_margin_for_every_motion_drawing(self):
        self.assertEqual(self.art.manifest['body_pixels'], 36)
        for armed in (True, False):
            for state in MOTION_STATES:
                family = 'armed' if armed else 'unarmed'
                duration = self.art.manifest['animations'][state]['duration_ms']
                for time in range(0, duration, 20):
                    image, foot = frame(state, time, armed)
                    self.assertEqual(image.get_size(), (64, 64))
                    self.assertEqual(foot, (32, 56))
                    bounds = image.get_bounding_rect()
                    self.assertGreater(bounds.left, 0, (family, state, time))
                    self.assertLess(bounds.right, 64, (family, state, time))
                    self.assertGreater(bounds.top, 0, (family, state, time))
                    self.assertLessEqual(bounds.bottom, 57, (family, state, time))
                    pose = anchors(state, time, armed)
                    self.assertEqual(pose['foot'], foot)
                    self.assertEqual(pose['facing'], 'left')
                    for key in ('guard', 'blade_base', 'blade_tip', 'cast_origin'):
                        self.assertTrue(all(0 <= value < 64 for value in pose[key]))

    def test_run_loops_and_completed_actions_hold_their_final_drawing(self):
        for armed in (True, False):
            first = frame('run', 0, armed)[0]
            self.assertIs(first, frame('run', 540, armed)[0])
            self.assertIs(first, frame('run', -100, armed)[0])
            for state in MOTION_STATES - {'run'}:
                last = frame(state, 100000, armed)[0]
                self.assertIs(last, frame(state, 200000, armed)[0])
            with self.assertRaises(ValueError):
                frame('run', float('nan'), armed)

    def test_weapon_and_cast_anchors_share_body_frame_selection(self):
        legacy = prepare_combat_art()
        for time in (0, 89, 90, 179, 1000):
            self.assertIs(legacy.frame('slash', time)[0], frame('slash', time)[0])
            self.assertEqual(legacy.anchors('slash', time), anchors('slash', time))
        release = anchors('cast_release', 0, True)
        self.assertLess(release['cast_origin'][0], release['foot'][0])
        self.assertEqual(release['cast_origin'], release['hand'])
        self.assertNotEqual(release['cast_origin'], release['blade_tip'])
        self.assertNotEqual(pygame.image.tobytes(frame('slash', 100, True)[0], 'RGBA'),
                            pygame.image.tobytes(frame('slash', 100, False)[0], 'RGBA'))
        self.assertFalse(anchors('slash', 100, False)['armed'])

    def test_original_sixteen_and_focus_aether_drawings_remain_available(self):
        legacy = prepare_combat_art()
        states = ('idle', 'attack', 'cast', 'guard', 'hurt', 'victory', 'defeat')
        self.assertEqual(sum(len(legacy.sequences[state]) for state in states), 16)
        self.assertEqual(len(legacy.sequences['focus_adjust']), 4)
        self.assertEqual(len(legacy.sequences['aether_edge']), 8)
        for state in (*states, 'focus_adjust', 'aether_edge'):
            self.assertIs(frame(state, 500)[0], legacy.frame(state, 500)[0])

    def test_ready_bank_never_reads_or_transforms_during_render(self):
        with patch('pygame.image.load', side_effect=AssertionError('Late asset read')), \
                patch('pygame.transform.scale', side_effect=AssertionError('Late body transform')):
            for armed in (True, False):
                for state in (*MOTION_STATES, 'aether_edge', 'idle'):
                    frame(state, 170, armed)
                    anchors(state, 170, armed)

    def test_immutable_generated_source_provenance(self):
        record = json.loads((FOLDER / 'provenance.json').read_text())
        self.assertEqual(record['generated_with'], 'image_gen')
        for source in record['sources']:
            path = FOLDER / source['file']
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), source['sha256'])
            self.assertEqual(source['drawings'], 36)
            self.assertEqual(source['scale'] * source['standing_source_body_pixels'], 36)


if __name__ == '__main__':
    unittest.main()
