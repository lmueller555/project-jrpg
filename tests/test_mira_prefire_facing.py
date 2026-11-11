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

    def test_registered_cuff_emitter_stays_attached_through_the_sight_orbit(self):
        for frame in range(792, 819):
            time=frame/60
            key,image,data,camera,positions=self.sample(time)
            self.assertTrue(key.startswith('aim_'))
            point=data['manifest']['animations'][key]['frames'][0]['emitter']
            self.assertGreater(image.get_at(point).a,0)
            emitted=camera.project(self.stage.mira_emitter_world(time,camera,positions['mira']))
            actor=camera.project(positions['mira'])
            scale=camera.focal*1.85/actor[2]/data['body_pixels']
            expected=pygame.Vector2(actor[:2])+(pygame.Vector2(point)-pygame.Vector2(data['anchor']))*scale
            self.assertLess(expected.distance_to(emitted[:2]),.001)

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

    def test_current_firing_and_loading_art_remains_seekable_and_registered(self):
        for time in (10.6,11.5,12.35,12.8,14.2,14.35,15.0,20.0):
            key,image,data,_,_=self.sample(time)
            self.assertEqual(image.get_size(),(128,128))
            self.assertEqual(data['anchor'],(64,116))
            self.assertTrue(image.get_bounding_rect().height)
            self.assertEqual(pygame.image.tobytes(image,'RGBA'),
                             pygame.image.tobytes(self.sample(time)[1],'RGBA'))


if __name__=='__main__':unittest.main()
