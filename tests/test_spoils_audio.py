"""Reward cues respect effects preferences and never control other voices."""
from array import array
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from audio_settings import AudioSettings
from spoils_audio import DURATIONS, GAINS, SpoilsAudio, _samples


class FakeSound:
    def __init__(self, *, buffer):
        self.buffer = buffer


class FakeChannel:
    def __init__(self):
        self.sound = None
        self.busy = False
        self.plays = []
        self.volume = 1.
        self.paused = False
        self.stops = self.pauses = self.unpauses = 0
        self.fades = []

    def play(self, sound, **options):
        self.sound, self.busy = sound, True
        self.plays.append(options)

    def get_sound(self):return self.sound
    def get_busy(self):return self.busy
    def set_volume(self, value):self.volume = value
    def fadeout(self, milliseconds):self.fades.append(milliseconds)
    def stop(self):
        self.sound, self.busy = None, False
        self.stops += 1
    def pause(self):
        self.paused = True
        self.pauses += 1
    def unpause(self):
        self.paused = False
        self.unpauses += 1


class FakeMixer:
    def __init__(self, *, ready=True, count=4):
        self.ready = ready
        self.initializations = 0
        self.channels = [FakeChannel() for _ in range(count)]
        self.sounds = []
        self.music = SimpleNamespace(stop=lambda: (_ for _ in ()).throw(
            AssertionError('Reward effects touched music')))

    def get_init(self):return (22050, -16, 2) if self.ready else None
    def init(self):
        self.initializations += 1
        self.ready = True
    def Sound(self, *, buffer):
        sound = FakeSound(buffer=buffer)
        self.sounds.append(sound)
        return sound
    def find_channel(self):
        return next((channel for channel in self.channels if not channel.busy), None)


class SpoilsAudioTests(unittest.TestCase):
    def make_audio(self, *, mixer=None, volume=1):
        settings = AudioSettings()
        settings.effects_volume = volume
        mixer = mixer or FakeMixer()
        audio = SpoilsAudio(SimpleNamespace(audio=settings), mixer=mixer)
        self.addCleanup(audio.stop)
        return audio, settings, mixer

    def test_muted_events_do_not_initialize_audio_or_generate_samples(self):
        audio, _, mixer = self.make_audio(mixer=FakeMixer(ready=False), volume=0)
        with patch('spoils_audio._samples', side_effect=AssertionError('Muted synthesis')):
            audio.start_fill()
            audio.level_up()
        self.assertEqual(mixer.initializations, 0)
        self.assertFalse(mixer.sounds)

    def test_fill_is_cached_and_repeated_start_does_not_restart_or_steal(self):
        audio, _, mixer = self.make_audio()
        audio.start_fill()
        first = audio._fill
        audio.start_fill()
        self.assertIs(audio._fill, first)
        self.assertEqual(len(mixer.sounds), 1)
        self.assertEqual(first[0].plays, [{'loops': -1, 'fade_ms': 24}])
        self.assertAlmostEqual(first[0].volume, GAINS['fill'])
        audio.stop_fill()
        self.assertEqual(first[0].fades, [40])
        self.assertFalse(audio._fill_requested)
        audio.level_up()
        self.assertEqual(len(mixer.sounds), 2)
        self.assertEqual(audio._voices[-1][0].plays[-1]['loops'], 0)

    def test_live_effects_volume_and_mute_resume_only_an_active_fill(self):
        audio, settings, mixer = self.make_audio()
        audio.start_fill()
        channel = audio._fill[0]
        settings.set_effects(.5)
        self.assertAlmostEqual(channel.volume, GAINS['fill'] * .5)
        settings.set_effects(0)
        self.assertFalse(channel.busy)
        settings.set_effects(.8)
        self.assertIsNotNone(audio._fill)
        self.assertEqual(len(mixer.sounds), 1)
        self.assertAlmostEqual(audio._fill[0].volume, GAINS['fill'] * .8)
        audio.level_up()
        settings.set_effects(0)
        count = sum(len(ch.plays) for ch in mixer.channels)
        settings.set_effects(.8)
        self.assertEqual(sum(len(ch.plays) for ch in mixer.channels), count)

    def test_pause_freezes_owned_channels_and_mute_never_unpauses_them(self):
        audio, settings, _ = self.make_audio()
        audio.start_fill()
        channel = audio._fill[0]
        audio.set_paused(True)
        self.assertEqual(channel.pauses, 1)
        audio.set_paused(True)
        self.assertEqual(channel.pauses, 1)
        settings.set_effects(.4)
        self.assertEqual(channel.unpauses, 0)
        audio.level_up()  # A paused event is dropped, never queued.
        self.assertEqual(len(audio._voices), 1)
        audio.set_paused(False)
        self.assertEqual(channel.unpauses, 1)

    def test_channel_reuse_and_disposal_cannot_stop_someone_elses_effect(self):
        audio, settings, _ = self.make_audio()
        audio.start_fill()
        channel = audio._fill[0]
        channel.sound = object()  # Our old sound has finished; another owner plays.
        audio.set_paused(True)
        settings.set_effects(0)
        audio.stop()
        self.assertEqual(channel.stops, 0)
        self.assertEqual(channel.pauses, 0)
        audio.set_paused(False)
        settings.set_effects(1)
        self.assertIsNone(audio._fill)

    def test_no_free_channel_drops_chime_without_stealing_and_fill_can_retry(self):
        mixer = FakeMixer(count=1)
        channel = mixer.channels[0]
        channel.sound, channel.busy = object(), True
        audio, settings, _ = self.make_audio(mixer=mixer)
        audio.start_fill()
        audio.level_up()
        self.assertIsNone(audio._fill)
        self.assertEqual(channel.stops, 0)
        channel.busy = False
        audio.start_fill()
        self.assertIsNotNone(audio._fill)
        self.assertEqual(channel.plays[-1]['loops'], -1)

    def test_device_failure_is_silent_and_safe(self):
        audio, _, mixer = self.make_audio(mixer=FakeMixer(ready=False))
        with patch.object(mixer, 'init', side_effect=pygame.error('No audio output')):
            audio.start_fill()
            audio.level_up()
            audio.set_paused(True)
            audio.stop()
        self.assertFalse(mixer.sounds)

    def test_pcm_is_short_bounded_and_ends_at_silence_without_music_assets(self):
        for cue in DURATIONS:
            with self.subTest(cue=cue):
                data = _samples(cue, 22050, 2)
                self.assertIsInstance(data, array)
                self.assertEqual(len(data), round(22050 * DURATIONS[cue]) * 2)
                self.assertEqual(list(data[:2]), [0, 0])
                self.assertEqual(list(data[-2:]), [0, 0])
                self.assertGreater(max(data), 1000)
                self.assertLess(max(abs(value) for value in data), 20000)

    def test_real_dummy_mixer_plays_and_disposes_both_original_cues(self):
        pygame.mixer.init(frequency=22050, size=-16, channels=2)
        self.addCleanup(pygame.mixer.quit)
        settings = AudioSettings()
        audio = SpoilsAudio(SimpleNamespace(audio=settings))
        self.addCleanup(audio.stop)
        audio.start_fill()
        self.assertIsNotNone(audio._fill)
        self.assertTrue(audio._fill[0].get_busy())
        audio.level_up()
        self.assertTrue(audio._voices)
        self.assertEqual(len(audio._sounds), 2)
        for (cue, _), sound in audio._sounds.items():
            self.assertAlmostEqual(sound.get_length(), DURATIONS[cue], delta=.001)
        audio.stop()
        self.assertIsNone(audio._fill)
        self.assertFalse(audio._voices)
