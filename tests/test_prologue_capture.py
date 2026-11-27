"""Review clips retain authored offsets and representative non-eagle timing."""
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import wave

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import numpy as np
import pygame

from tools.capture_fire_veinhold_opening import (clip_spec, audio_preview, _sample_frames,
                                               _production_picture_tap)
from tools.capture_gallery import thumbnail_ready


class PrologueCaptureTests(unittest.TestCase):
    def test_production_tap_copies_once_before_ui_decorates_the_picture(self):
        class Scene:
            calls = 0
            def render_frame(self):
                self.calls += 1
                image = pygame.Surface((16, 12))
                image.fill('#123456')
                return image
        scene = Scene()
        with _production_picture_tap(scene) as picture:
            decorated = scene.render_frame()
            pygame.draw.rect(decorated, '#ffffff', (0, 8, 16, 4))
            self.assertEqual(scene.calls, 1)
            self.assertEqual(picture['calls'], 1)
            self.assertEqual(picture['frame'].get_at((2, 10))[:3], (18, 52, 86))
            self.assertEqual(decorated.get_at((2, 10))[:3], (255, 255, 255))
        self.assertNotIn('render_frame', vars(scene))

    def test_production_tap_restores_an_existing_override_after_failure(self):
        original = lambda:pygame.Surface((2, 2))
        scene = SimpleNamespace(render_frame=original)
        with self.assertRaisesRegex(RuntimeError, 'encoder'):
            with _production_picture_tap(scene):
                scene.render_frame()
                raise RuntimeError('encoder failed')
        self.assertIs(scene.render_frame, original)

    def test_complete_and_late_clip_have_exact_authored_offsets(self):
        complete = clip_spec()
        self.assertEqual(complete['duration'], 42.)
        self.assertEqual(complete['offset'], 0.)
        expected = (('eagle_ascent', 0., 25.), ('island_orbit', 25., 5.),
                    ('alarm_hold', 30., 4.), ('bridge_rush', 34., 1.),
                    ('frozen_bridge', 35., 4.), ('bridge_running', 39., 3.))
        for index, (identifier, offset, duration) in enumerate(expected, 1):
            with self.subTest(clip=identifier):
                spec = clip_spec(identifier)
                self.assertEqual((spec['offset'], spec['duration']), (offset, duration))
                self.assertEqual(clip_spec(f'fire_veinhold_shot_{index:02d}'), spec)
        with self.assertRaises(ValueError):clip_spec('not_implemented')

    def test_rush_thumbnail_is_reachable_before_one_second_completion(self):
        game = SimpleNamespace(cinematic=SimpleNamespace(elapsed=.69))
        self.assertFalse(thumbnail_ready('fire_veinhold_shot_04', game, .69))
        game.cinematic.elapsed = .7
        self.assertTrue(thumbnail_ready('fire_veinhold_shot_04', game, .7))

    def test_complete_thumbnail_uses_the_running_clip_before_completion(self):
        from fire_veinhold_opening import available_shots
        shots = available_shots()
        self.assertEqual(shots[-1]['id'], 'bridge_running')
        cue = 39.+shots[-1]['thumbnail_time']
        game = SimpleNamespace(cinematic=SimpleNamespace(elapsed=cue-.01))
        self.assertFalse(thumbnail_ready('fire_veinhold_opening', game, cue-.01))
        game.cinematic.elapsed = cue
        self.assertTrue(thumbnail_ready('fire_veinhold_opening', game, cue))
        self.assertLess(cue, 42.)

    def test_representative_complete_frames_include_new_boundaries(self):
        spec = clip_spec()
        frames = _sample_frames(spec, 60, 2520)
        self.assertTrue({1500,1800,2040,2100,2340,2370,2430,2490,2519} <= frames)
        self.assertTrue(all(0 <= index < 2520 for index in frames))

    def test_running_capture_starts_at_contact_audio_clock_without_eagle_cues(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'running.wav'
            metadata = audio_preview(path, seconds=3., start_seconds=39.)
            self.assertEqual(metadata['global_start_seconds'], 39.)
            self.assertEqual(metadata['events'], [])
            self.assertEqual(metadata['running']['start_global_seconds'], 39.)
            self.assertGreater(metadata['peak'], .01)
            self.assertLess(metadata['peak'], 1.)
            with wave.open(str(path), 'rb') as stream:
                self.assertEqual(stream.getnframes(), 3*48000)

    def test_late_capture_contains_alarm_without_replaying_eagle_cues(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'bridge.wav'
            metadata = audio_preview(path, seconds=1., start_seconds=34.)
            self.assertEqual(metadata['global_start_seconds'], 34.)
            self.assertEqual(metadata['events'], [])
            self.assertEqual(metadata['alert']['rush_start_global_seconds'], 34.)
            self.assertGreater(metadata['peak'], .01)
            self.assertLess(metadata['peak'], 1.)
            with wave.open(str(path), 'rb') as stream:
                self.assertEqual(stream.getnchannels(), 2)
                self.assertEqual(stream.getframerate(), 48000)
                self.assertEqual(stream.getnframes(), 48000)

    def test_industrial_mix_starts_at_25_while_alarm_stays_off_until_30(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'orbit.wav'
            with patch('prologue_alert_audio.mix_alert_audio', return_value=np.zeros((48000, 2))) as alert:
                early = audio_preview(path, seconds=1., start_seconds=24.)
                alert.assert_not_called()
                before = audio_preview(path, seconds=1., start_seconds=29.)
                alert.assert_called_once_with(29., 1., sample_rate=48000)
                after = audio_preview(path, seconds=1., start_seconds=30.)
                self.assertEqual(alert.call_args.args, (30., 1.))
                self.assertEqual(alert.call_count, 2)
            self.assertIsNone(early['machinery'])
            self.assertIsNotNone(before['machinery'])
            self.assertIsNone(before['alert'])
            self.assertIsNotNone(after['alert'])


if __name__ == '__main__':unittest.main()
