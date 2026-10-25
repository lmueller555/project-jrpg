"""Morning cues stay local, quiet when disabled, and safe without a device."""
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

from array import array
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import pygame
from opening_audio import MorningAudio


class FakeSound:
    def __init__(self, buffer):
        self.buffer = buffer
        self.set_volume = Mock()
        self.channels = []
        self.options = []

    def play(self, **options):
        channel = Mock()
        channel.get_sound.return_value = self
        self.channels.append(channel)
        self.options.append(options)
        return channel


class OpeningAudioTests(unittest.TestCase):
    def game(self, stage='wake', music=True):
        return SimpleNamespace(opening=SimpleNamespace(stage=stage),
                               title=SimpleNamespace(music_enabled=music), on_title=False)

    def mixer(self):
        spec = patch('opening_audio.pygame.mixer.get_init', return_value=(22050, -16, 2))
        sounds = patch('opening_audio.pygame.mixer.Sound', side_effect=FakeSound)
        spec.start();sounds.start()
        self.addCleanup(spec.stop);self.addCleanup(sounds.stop)

    def test_muted_and_disabled_openings_never_initialize_audio(self):
        with patch('opening_audio.pygame.mixer.init') as init, \
             patch('opening_audio.pygame.mixer.get_init') as spec:
            for stage, music in (('wake', False), ('disabled', True), ('assignment', True), ('done', True)):
                MorningAudio(self.game(stage, music)).update(.1)
            init.assert_not_called();spec.assert_not_called()

    def test_missing_audio_device_is_nonfatal_and_not_retried_every_frame(self):
        audio = MorningAudio(self.game())
        with patch('opening_audio.pygame.mixer.get_init', return_value=None), \
             patch('opening_audio.pygame.mixer.init', side_effect=pygame.error('no device')) as init:
            audio.update(.1);audio.update(.1)
            init.assert_called_once_with()
            audio.reset();audio.update(.1)
            self.assertEqual(init.call_count, 2)

    def test_wake_cues_play_once_and_stream_loops_without_touching_music(self):
        self.mixer()
        game = self.game()
        audio = MorningAudio(game)
        with patch('opening_audio.pygame.mixer.music.stop') as stop_music:
            audio.update(.1)
            for _ in range(40):audio.update(.1)
            bell = audio._sounds[('bell', 22050, 2)]
            knock = audio._sounds[('knock', 22050, 2)]
            stream = audio._sounds[('stream', 22050, 2)]
            self.assertEqual(len(bell.options), 1)
            self.assertEqual(len(knock.options), 1)
            self.assertEqual(stream.options, [{'loops': -1, 'fade_ms': 600}])
            self.assertEqual(len(audio._sounds[('birds', 22050, 2)].options), 1)
            game.opening.stage = 'explore';audio.update(1)
            game.opening.stage = 'breakfast';audio.update(1)
            self.assertEqual(len(bell.options), 1)
            game.opening.stage = 'assignment';audio.update(.1)
            stream.channels[0].fadeout.assert_called_once_with(250)
            self.assertFalse(audio._channels)
            audio.update(.1)
            stream.channels[0].fadeout.assert_called_once_with(250)
            audio.reset()
            stream.channels[0].stop.assert_called_once_with()
            stop_music.assert_not_called()

    def test_reset_stops_only_channels_still_owned_and_rearms_wake(self):
        self.mixer()
        audio = MorningAudio(self.game())
        audio.update(.1)
        bell = audio._sounds[('bell', 22050, 2)]
        knock = audio._sounds[('knock', 22050, 2)]
        bell.channels[0].get_sound.return_value = object()
        audio.reset()
        bell.channels[0].stop.assert_not_called()
        knock.channels[0].stop.assert_called_once_with()
        self.assertFalse(audio._wake_played)
        audio.update(.1)
        self.assertEqual(len(bell.options), 2)

    def test_continue_into_exploration_has_ambience_without_replaying_knocks(self):
        self.mixer()
        audio = MorningAudio(self.game('explore'))
        audio.update(1)
        self.assertIn(('stream', 22050, 2), audio._sounds)
        self.assertNotIn(('knock', 22050, 2), audio._sounds)
        self.assertNotIn(('bell', 22050, 2), audio._sounds)

    def test_pcm_is_stereo_int16_and_cues_have_soft_boundaries(self):
        for name in ('bell', 'knock', 'birds', 'stream'):
            pcm = MorningAudio._samples(name, 8000, 2)
            self.assertIsInstance(pcm, array)
            self.assertEqual(pcm.typecode, 'h')
            self.assertEqual(list(pcm[::2]), list(pcm[1::2]))
            self.assertLess(max(abs(value) for value in pcm), 32767)
            if name == 'stream':
                self.assertLess(abs(pcm[0]-pcm[-2]), 4000)
            else:
                self.assertEqual(pcm[0], 0)
                self.assertLess(abs(pcm[-2]), 30)


if __name__ == '__main__':unittest.main()
