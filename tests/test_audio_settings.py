"""Independent volume persistence, muted restoration and nonfatal settings I/O."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
from audio_settings import AudioSettings


class AudioSettingsTests(unittest.TestCase):
    def test_older_volume_only_settings_keep_interface_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'settings.json'
            path.write_text(json.dumps({'version': 1, 'music_volume': .4,
                                        'effects_volume': .7, 'last_music': .4,
                                        'last_effects': .7}))
            settings = AudioSettings(path)
            self.assertEqual((settings.music_volume, settings.effects_volume), (.4, .7))
            self.assertEqual((settings.text_scale, settings.reduced_motion,
                              settings.tracker_visible), (1, False, True))
            self.assertIsNone(settings.error)

    def test_interface_preferences_roundtrip_with_volumes_and_reject_invalid_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'settings.json'
            settings = AudioSettings(path)
            settings.set_music(.6)
            self.assertTrue(settings.set_text_scale(1.5))
            self.assertTrue(settings.set_reduced_motion(True))
            self.assertTrue(settings.set_tracker_visible(False))
            for invalid in (True, 0, -1, 1.2, float('nan'), float('inf'), 'large'):
                self.assertFalse(settings.set_text_scale(invalid))
            self.assertFalse(settings.set_reduced_motion(1))
            self.assertFalse(settings.set_tracker_visible('yes'))
            loaded = AudioSettings(path)
            self.assertEqual((loaded.music_volume, loaded.text_scale,
                              loaded.reduced_motion, loaded.tracker_visible), (.6, 1.5, True, False))
            loaded.toggle_reduced_motion()
            loaded.toggle_tracker()
            restored = AudioSettings(path)
            self.assertEqual((restored.reduced_motion, restored.tracker_visible), (False, True))

    def test_malformed_optional_preferences_do_not_discard_valid_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'settings.json'
            data = AudioSettings().to_dict()
            data.update(music_volume=.3, effects_volume=.2, text_scale=True,
                        reduced_motion='yes', tracker_visible=0)
            path.write_text(json.dumps(data))
            loaded = AudioSettings(path)
            self.assertEqual((loaded.music_volume, loaded.effects_volume), (.3, .2))
            self.assertEqual((loaded.text_scale, loaded.reduced_motion,
                              loaded.tracker_visible), (1, False, True))

    def test_levels_are_independent_clamped_and_retain_mute_level(self):
        settings = AudioSettings()
        settings.set_music(.6)
        settings.set_effects(.3)
        self.assertEqual((settings.music_volume, settings.effects_volume), (.6, .3))
        settings.toggle_music()
        self.assertEqual((settings.music_volume, settings.effects_volume), (0, .3))
        settings.toggle_music()
        self.assertEqual(settings.music_volume, .6)
        settings.set_effects(2)
        settings.set_music(-20)
        self.assertEqual((settings.music_volume, settings.effects_volume), (0, 1))
        settings.toggle_music()
        self.assertEqual(settings.music_volume, .6)
        self.assertFalse(settings.set_effects(float('nan')))
        self.assertFalse(settings.set_music(float('inf')))
        self.assertFalse(settings.set_music(True))
        settings.set_music(10**400)
        self.assertEqual(settings.music_volume, 1)

    def test_separate_settings_file_roundtrips_without_touching_journey(self):
        with tempfile.TemporaryDirectory() as directory:
            settings_path = Path(directory)/'settings.json'
            journey = Path(directory)/'journey.json'
            journey.write_text('{"quest":"unchanged"}')
            settings = AudioSettings(settings_path)
            settings.set_music(.4)
            settings.set_effects(.8)
            settings.toggle_music()
            loaded = AudioSettings(settings_path)
            self.assertEqual((loaded.music_volume, loaded.effects_volume), (0, .8))
            loaded.toggle_music()
            self.assertEqual(loaded.music_volume, .4)
            self.assertEqual(journey.read_text(), '{"quest":"unchanged"}')
            self.assertEqual(json.loads(settings_path.read_text())['music_volume'], .4)

    def test_invalid_settings_keep_defaults_and_prior_file_intact(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'settings.json'
            for raw in ('{unfinished', '{"version":true}',
                        json.dumps({'version': 1, 'music_volume': 10**400,
                                    'effects_volume': .3, 'last_music': .5, 'last_effects': .5})):
                with self.subTest(raw=raw[:30]):
                    path.write_text(raw)
                    settings = AudioSettings(path)
                    self.assertEqual((settings.music_volume, settings.effects_volume), (1, 1))
                    self.assertIsNotNone(settings.error)
                    self.assertEqual(path.read_text(), raw)

    def test_failed_write_is_nonfatal_and_preserves_last_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'settings.json'
            settings = AudioSettings(path)
            settings.set_music(.8)
            prior = path.read_bytes()
            with patch('save_game.os.replace', side_effect=OSError('read only')):
                self.assertTrue(settings.set_effects(.3))
            self.assertIsNotNone(settings.error)
            self.assertEqual(path.read_bytes(), prior)
            self.assertEqual(settings.effects_volume, .3)

    def test_music_mix_uses_existing_base_and_missing_mixer_is_safe(self):
        settings = AudioSettings()
        with patch('pygame.mixer.get_init', return_value=(44100, -16, 2)), \
                patch('pygame.mixer.music.set_volume') as volume:
            settings.set_music(.5)
            volume.assert_called_once_with(.225)
        with patch('pygame.mixer.get_init', return_value=None), \
                patch('pygame.mixer.music.set_volume') as volume:
            settings.set_music(.8)
            volume.assert_not_called()
        with patch('pygame.mixer.get_init', side_effect=pygame.error('device lost')):
            settings.set_music(.7)


if __name__ == '__main__':unittest.main()
