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

from tools.capture_fire_veinhold_opening import clip_spec, audio_preview, _sample_frames
from tools.capture_gallery import thumbnail_ready


class PrologueCaptureTests(unittest.TestCase):
    def test_complete_and_late_clip_have_exact_authored_offsets(self):
        complete = clip_spec()
        self.assertEqual(complete['duration'], 39.)
        self.assertEqual(complete['offset'], 0.)
        expected = (('eagle_ascent', 0., 25.), ('island_orbit', 25., 5.),
                    ('alarm_hold', 30., 4.), ('bridge_rush', 34., 1.),
                    ('frozen_bridge', 35., 4.))
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

    def test_representative_complete_frames_include_new_boundaries(self):
        spec = clip_spec()
        frames = _sample_frames(spec, 60, 2340)
        self.assertTrue({1500,1800,2040,2100,2339} <= frames)
        self.assertTrue(all(0 <= index < 2340 for index in frames))

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
