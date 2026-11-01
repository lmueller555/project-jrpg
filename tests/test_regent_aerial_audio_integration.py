"""Real Gallery playback owns its bird voices and moving-caravan sounds."""
import os
from pathlib import Path
import tempfile
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame

from main import Game
from test_mill_battle_gameplay import key


class RegentAerialAudioIntegrationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='arrival-audio-gallery-')
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name)/'journey.json'
        self.game = Game(fullscreen=False, start_on_title=True, save_path=self.path,
                         settings_path=Path(directory.name)/'settings.json')
        self.game.audio.set_music(0)
        self.game.audio.set_effects(1)
        self.assertTrue(self.game.open_gallery())
        self.assertTrue(self.game.launch_gallery_scene('regent_arrival'))
        self.scene = self.game.gallery_session.game.regent_arrival

    def tearDown(self):
        if self.game.gallery_session is not None:self.game.gallery_session.close()
        self.game.regent_arrival.bird_audio.stop()
        self.game.opening_audio.reset()
        self.game.regional_audio.reset()
        self.game.music.stop()
        pygame.quit()

    def until(self, predicate):
        for _ in range(2000):
            if predicate():return
            self.game.update(1/30, (0, 0), False)
        self.fail(('Cue not reached', self.scene.shot, self.scene.phase_time))

    def test_real_hawk_voice_pauses_and_gallery_exit_releases_only_owned_sound(self):
        before = self.path.read_bytes() if self.path.exists() else None
        self.until(lambda:'hawk_call' in self.scene.bird_audio.voices)
        voice = self.scene.bird_audio.voices['hawk_call']
        self.assertGreater(voice.sound.get_length(), .5)
        key(self.game, pygame.K_p)
        self.assertTrue(self.scene.paused)
        self.assertTrue(self.scene.bird_audio._paused)
        clock = self.scene.phase_time
        self.game.update(1., (0, 0), False)
        self.assertEqual(self.scene.phase_time, clock)
        self.assertIs(voice.channel.get_sound(), voice.sound)

        rate, sample_format, channels = pygame.mixer.get_init()
        self.assertEqual(sample_format, -16)
        unrelated = pygame.mixer.Sound(buffer=b'\0\0'*(rate*channels*2))
        channel = unrelated.play()
        self.assertIsNotNone(channel)
        key(self.game, pygame.K_ESCAPE)
        self.assertIsNone(self.game.gallery_session)
        self.assertEqual(self.scene.bird_audio.voices, {})
        self.assertIs(channel.get_sound(), unrelated)
        self.assertEqual(self.path.read_bytes() if self.path.exists() else None, before)
        channel.stop()

    def test_travel_sound_matches_actual_ground_motion_and_stops_for_greeting(self):
        self.assertEqual(self.scene.shot, 'mill_close')
        self.assertIsNone(self.scene._audio_mode())
        self.until(lambda:(self.scene.aerial_snapshot() or {}).get('ground_handoff', False))
        before = self.scene.aerial_snapshot()
        self.assertEqual(self.scene._audio_mode(before), 'travel')
        travel_clock = self.scene.audio.travel
        self.game.update(.2, (0, 0), False)
        after = self.scene.aerial_snapshot()
        gait_advance = (after['projected_actors']['aldric']['gait_clock']-
                        before['projected_actors']['aldric']['gait_clock'])
        self.assertAlmostEqual(self.scene.audio.travel-travel_clock, gait_advance)
        for actor in ('aldric', 'caravan'):
            self.assertLess(after['projected_actors'][actor]['native_xy'][0],
                            before['projected_actors'][actor]['native_xy'][0])
        self.until(lambda:self.scene.shot == 'gate_greeting')
        self.game.update(.05, (0, 0), False)
        self.assertIsNone(self.scene._audio_mode())
        self.assertEqual(self.scene.audio.channels, [])
        self.assertEqual(self.scene.bird_audio.voices, {})


if __name__ == '__main__':unittest.main()
