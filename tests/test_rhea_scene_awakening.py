"""The approved awakening stays in one world with one full-body Rhea."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
import pygame

from ice_reaper_action import IceReaperActionStage
from rhea_scene_awakening import RheaSceneAwakening


ROOT = Path(__file__).resolve().parents[1]


class RheaSceneAwakeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((480, 320))
        cls.stage = IceReaperActionStage(ROOT/'assets/story/ice_reaper_rescue', strict=True)
        cls.awakening = cls.stage.awakening

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def render(self, local, reduced=False):
        canvas = pygame.Surface((480, 320))
        self.stage.draw(canvas, 15.1+local, reduced)
        return pygame.image.tobytes(canvas, 'RGB')

    def test_production_loads_full_body_frames_without_the_rejected_portrait(self):
        loaded = []
        original = pygame.image.load
        def record(path, *args, **kwargs):
            loaded.append(str(path))
            return original(path, *args, **kwargs)
        with patch('pygame.image.load', side_effect=record):
            stage = IceReaperActionStage(ROOT/'assets/story/ice_reaper_rescue', strict=True)
        self.assertFalse(hasattr(stage, 'rhea_closeup'))
        self.assertFalse(any('ice_reaper_rhea_closeup' in name for name in loaded))
        self.assertFalse(any('/ice_reaper_rescue/actors/rhea/eyes_' in name for name in loaded))
        self.assertEqual(len(stage.awakening.expression_images), 8)
        self.assertTrue(all(image.get_size() == (128, 128)
                            for image in stage.awakening.expression_images.values()))

    def test_expression_frames_preserve_the_existing_body_hair_staff_and_alpha(self):
        manifest = self.awakening.expression_manifest
        source = pygame.image.load(str(ROOT/manifest['source']))
        original = pygame.surfarray.array3d(source)
        alpha = pygame.surfarray.array_alpha(source)
        protected = np.ones(original.shape[:2], dtype=bool)
        for row, (start, end) in manifest['facial_mask_rows'].items():
            protected[start:end+1, int(row)] = False
        drawings = set()
        for name, frame in self.awakening.expression_images.items():
            with self.subTest(expression=name):
                np.testing.assert_array_equal(pygame.surfarray.array3d(frame)[protected],
                                              original[protected])
                np.testing.assert_array_equal(pygame.surfarray.array_alpha(frame), alpha)
                drawings.add(pygame.image.tobytes(frame, 'RGBA'))
        self.assertEqual(len(drawings), 8)
        self.assertEqual(manifest['anchor'], [64, 116])

    def test_closed_eyes_build_strain_before_the_angry_green_opening(self):
        for local, expression in ((.1, 'neutral_closed'), (.6, 'strain_begin'),
                                  (.9, 'strain_mid'), (1.2, 'strain_peak')):
            with self.subTest(local=local):
                state = self.awakening.state(local)
                self.assertEqual(state['expression'], expression)
                self.assertTrue(state['eyes_closed'])
                self.assertEqual(state['green_light'], (0., 0.))
        self.assertEqual(self.awakening.state(1.35)['expression'], 'opening_01')
        self.assertEqual(self.awakening.state(1.5)['expression'], 'opening_02')
        self.assertEqual(self.awakening.state(1.7)['expression'], 'angry_open')
        self.assertEqual(self.awakening.state(2.)['expression'], 'angry_hold')
        glow, gleam = self.awakening.state(1.52)['green_light']
        self.assertGreater(glow, .5)
        self.assertGreater(gleam, .95)
        self.assertEqual(self.awakening.state(1.9)['green_light'], (1., 0.))

    def test_actual_draw_trace_contains_one_rhea_and_only_the_original_prison(self):
        for local in (0., .4, 1., 1.52, 2., 2.2, 2.3, 2.4, 2.85, 4., 5.7):
            with self.subTest(local=local):
                self.render(local)
                trace = self.awakening.last_draw_trace
                bodies = [entry for entry in trace if entry.get('actor') == 'rhea']
                self.assertEqual(len(bodies), 1)
                self.assertEqual(bodies[0]['source_canvas'], [128, 128])
                prison = [entry for entry in trace if 'prison_layer' in entry]
                self.assertEqual([entry['prison_layer'] for entry in prison],
                                 ['back', 'front'] if local < 2.35 else [])
                self.assertTrue(all(entry['source'] == 'original_scene_prison'
                                    for entry in prison))

    def test_shatter_starts_the_fast_retreat_before_the_shoulder_sweep(self):
        self.assertEqual(self.stage.telemetry(17.29)['prison'], 'cracked')
        self.assertEqual(self.stage.telemetry(17.3)['prison'], 'shattered')
        self.assertAlmostEqual(self.awakening.RETREAT_END-self.awakening.BREAKOUT, .65)
        self.assertEqual(self.awakening.camera(2.2), self.awakening.CLOSE)
        self.assertEqual(self.awakening.camera(2.85), self.awakening.WIDE)
        self.assertEqual(self.awakening.camera(2.85).position,
                         (5.020994, 16.3, -9.059998))
        for boundary in (2.2, 2.85, 5.15):
            before = self.awakening.camera(boundary-1e-6)
            after = self.awakening.camera(boundary+1e-6)
            self.assertLess(pygame.Vector3(before.position).distance_to(after.position), 1e-5)
            self.assertAlmostEqual(before.focal, after.focal, places=5)

    def test_sweep_moves_the_real_camera_between_shoulders_then_holds(self):
        first = self.awakening.camera(2.85)
        last = self.awakening.camera(5.15)
        self.assertGreater(pygame.Vector3(first.position).distance_to(last.position), 3.9)
        self.assertEqual(last.position, (1.6290008314606745, 16.3, -11.17999373033708))
        for local in (2.85, 3.5, 4., 4.8, 5.15, 5.7, 5.9):
            camera = self.awakening.camera(local)
            self.assertEqual(camera.target, (-3, .8, 0))
            self.assertEqual(camera.focal, 245)
        self.assertEqual(self.awakening.camera(5.9), last)

    def test_rhea_turns_toward_the_reaper_without_moving_from_her_prison(self):
        for local in (0., 1., 2.2, 2.5, 2.85, 4., 5.9):
            positions = self.stage.actor_positions(self.awakening.canonical_time(local))
            self.assertEqual(positions['rhea'], pygame.Vector3(-3, 0, 0))
        self.assertEqual(self.stage.actor_heading('rhea', 16.3), pygame.Vector3(0, 0, 1))
        positions = self.stage.actor_positions(16.95)
        intended = positions['ice_reaper']-positions['rhea']
        intended.y = 0
        self.assertGreater(self.stage.actor_heading('rhea', 16.95).dot(intended.normalize()), .999999)
        self.assertEqual(self.stage.reaper_position(16.95), self.stage.reaper_position(20.))

    def test_seek_pause_and_reduced_motion_do_not_accumulate_render_state(self):
        with patch('pygame.image.load', side_effect=AssertionError('draw loaded an asset')):
            for reduced in (False, True):
                for local in (1.52, 2.3, 4., 5.7):
                    expected = self.render(local, reduced)
                    self.render(.2, reduced)
                    self.stage.reset()
                    self.assertEqual(self.render(local, reduced), expected)
        for local in (2.2, 3., 4., 5.9):
            self.assertEqual(self.awakening.camera(local, reduced=True), self.awakening.WIDE)


if __name__ == '__main__':
    unittest.main()
