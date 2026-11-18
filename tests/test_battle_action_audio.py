"""Short action cues honor effect volume and stop cleanly on battle pause."""
import os
from pathlib import Path
import runpy
import tempfile
import wave
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame
from battle_action_audio import BattleActionAudio, LIMITS, SOURCES


class BattleActionAudioTests(unittest.TestCase):
    def tearDown(self):pygame.mixer.quit()

    def test_muted_cues_do_not_initialize_audio_or_read_assets(self):
        player=BattleActionAudio(SimpleNamespace(audio=SimpleNamespace(effects_volume=0)))
        with patch('pygame.mixer.Sound', side_effect=AssertionError('Muted asset read')):
            player.play('step')
        self.assertFalse(pygame.mixer.get_init())

    def test_recordings_are_shortened_and_cached_for_individual_action_beats(self):
        player=BattleActionAudio(SimpleNamespace(audio=SimpleNamespace(effects_volume=1)))
        for cue in SOURCES:
            player.play(cue)
            self.assertLessEqual(player._sounds[cue].get_length(), LIMITS[cue]+.001)
        recorded=player._sounds['step']
        player.play('step')
        self.assertIs(player._sounds['step'],recorded)
        player.stop()
        self.assertFalse(player._channels)

    def test_dry_bolt_contact_is_reproducible_short_and_unclipped(self):
        root = Path(__file__).resolve().parents[1]/'assets/audio/sfx/mira_bolt_shot'
        build = runpy.run_path(str(root/'build.py'))['build']
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'bolt.wav';build(path)
            self.assertEqual(path.read_bytes(), (root/'bolt_impact.wav').read_bytes())
            with wave.open(str(path)) as sound:
                self.assertEqual((sound.getnchannels(), sound.getsampwidth()), (1, 2))
                self.assertAlmostEqual(sound.getnframes()/sound.getframerate(), .096, places=4)
                from array import array
                samples = array('h');samples.frombytes(sound.readframes(sound.getnframes()))
                self.assertLess(max(map(abs, samples)), 32767)
                self.assertGreater(max(map(abs, samples)), 10000)

    def test_live_effect_volume_applies_without_reloading_recording(self):
        settings=SimpleNamespace(effects_volume=1)
        player=BattleActionAudio(SimpleNamespace(audio=settings))
        player.play('land');first=player._sounds['land'].get_volume()
        settings.effects_volume=.5
        player.play('land')
        self.assertLess(player._sounds['land'].get_volume(),first)
        player.stop()
