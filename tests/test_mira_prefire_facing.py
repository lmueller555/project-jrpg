"""Pre-fire aiming art follows the on-screen attack ray; firing stays intact."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import hashlib
from pathlib import Path
import unittest

import pygame

from ice_reaper_action import IceReaperActionStage


ROOT = Path(__file__).resolve().parents[1]
# Native drawing landmarks: rear of the launcher and its muzzle, independently
# checked on the actual unmodified directional PNGs. These describe image-space
# barrel axes, not the world heading which was already correct before the fix.
BARRELS = {
    'aim_front_left': ((57, 48), (45, 34)),
    'aim_left': ((52, 51), (31, 35)),
    'aim_rear_left': ((61, 48), (55, 34)),
}


class MiraPrefireFacingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((480, 320))
        cls.stage = IceReaperActionStage(ROOT/'assets/story/ice_reaper_rescue', strict=True)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def sample(self, time):
        positions = self.stage.actor_positions(time)
        camera = self.stage.camera(time)
        action, local, duration = self.stage._action('mira', time)
        key = self.stage.sequence_key('mira', action, local, duration, camera,
                                      positions['mira'], time)
        image, data = self.stage._sequence('mira', action, local, duration, camera,
                                           positions['mira'], time=time)
        return key, image, data, camera, positions

    def test_visible_barrel_points_toward_the_reaper_during_the_sight_orbit(self):
        for frame in range(792, 819):  # 13.2–13.633s, where the wrong facing was visible.
            time = frame/60
            with self.subTest(time=time):
                key, image, data, camera, positions = self.sample(time)
                self.assertIn(key, BARRELS)
                breech, muzzle = BARRELS[key]
                # Keep the annotation attached to actual opaque drawing pixels.
                self.assertGreater(image.get_at(breech).a, 0)
                self.assertGreater(image.get_at(muzzle).a, 0)
                actor = camera.project(positions['mira'])
                target = camera.project(positions['ice_reaper'])
                self.assertIsNotNone(target)
                scale = camera.focal*1.85/actor[2]/data['body_pixels']
                origin = pygame.Vector2(actor[:2])-pygame.Vector2(data['anchor'])*scale
                breech_screen = origin+pygame.Vector2(breech)*scale
                drawn_axis = pygame.Vector2(muzzle)-pygame.Vector2(breech)
                attack_ray = pygame.Vector2(target[:2])-breech_screen
                self.assertLess(drawn_axis.x, 0)
                self.assertLess(attack_ray.x, 0)
                self.assertLess(drawn_axis.y, 0)
                self.assertGreater(drawn_axis.normalize().dot(attack_ray.normalize()), .5)

    def test_four_drawings_bridge_loading_to_the_held_aim_without_extending_timing(self):
        sequence = self.stage.actors['mira']['sequences']['prefire_raise']
        self.assertEqual(len(sequence), 4)
        seen = set()
        for frame in range(741, 768):
            key, image, data, _, _ = self.sample(frame/60)
            self.assertEqual(key, 'prefire_raise')
            seen.add(next(index for index, (drawing, _) in enumerate(sequence) if image is drawing))
            self.assertEqual(image.get_size(), (128, 128))
            self.assertEqual(data['anchor'], (64, 116))
        self.assertEqual(seen, {0, 1, 2, 3})
        self.assertEqual(self.sample(12.35-1e-6)[0], 'load')
        self.assertNotEqual(self.sample(12.8)[0], 'prefire_raise')
        self.assertEqual(self.sample(14.2)[0], 'fire')

    def selection_digest(self, start, end):
        result = hashlib.sha256()
        for frame in range(start, end):
            key, image, _, _, _ = self.sample(frame/60)
            digest = hashlib.sha256(pygame.image.tobytes(image, 'RGBA')).hexdigest()
            result.update(f'{frame}:{key}:{digest}\n'.encode())
        return result.hexdigest()

    def test_every_firing_and_later_selection_matches_the_approved_baseline(self):
        self.assertEqual(self.selection_digest(852, 1920),
                         '3a1e220c977baa22c8bd5b736e019d9b2490616a84c7616626595e54d5624b18')

    def test_the_loading_drawings_before_the_new_raise_are_unchanged(self):
        self.assertEqual(self.selection_digest(636, 741),
                         '0fb7a1cde35863de1d824f2c647c3f9ded404c4f7e4aad388744f06e3fd10d6f')
