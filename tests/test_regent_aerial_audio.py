"""Bird effects follow authored wingbeats and release only their own voices."""
import json
import math
import os
from array import array
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock

os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame

from audio_settings import AudioSettings
from regent_aerial_audio import ASSETS, CALL_TIMES, GAINS, RegentAerialAudio


class Sound:
    def __init__(self, path):self.name = Path(path).stem
    def get_length(self):return .28 if self.name == 'wing_flap' else 1.4


class Channel:
    def __init__(self, events):
        self.events = events
        self.sound = None
        self.volume = None
        self.paused = False
        self.stops = self.volume_changes = 0

    def get_sound(self):return self.sound
    def set_volume(self, value):self.volume = value;self.volume_changes += 1
    def play(self, sound, loops=0):
        self.sound = sound
        self.events.append((sound.name, self.volume, loops))
    def stop(self):self.sound = None;self.stops += 1
    def pause(self):self.paused = True
    def unpause(self):self.paused = False


class Mixer:
    def __init__(self):
        self.ready = True
        self.events = []
        self.channels = [Channel(self.events) for _ in range(4)]
        self.music = MagicMock()
        self.stop = MagicMock()
        self.Sound = MagicMock(side_effect=Sound)
    def get_init(self):return (48000, -16, 2) if self.ready else None
    def find_channel(self):return next((c for c in self.channels if c.sound is None), None)


class RegentAerialAudioTests(unittest.TestCase):
    def setUp(self):
        self.game = SimpleNamespace(audio=AudioSettings(None))
        self.mixer = Mixer()
        self.audio = RegentAerialAudio(self.game, mixer=self.mixer)

    def snapshot(self, seconds, **bird):
        return {'seconds':seconds, 'bird':{'screen_xy':[240,160], 'bank':0., **bird}}

    def update(self, seconds, **bird):
        self.audio.update(.05, self.snapshot(seconds, **bird))

    def walk_to(self, end, **bird):
        start = self.audio._last_seconds or 0.
        while start < end:
            start = min(end, start+.05)
            self.update(start, **bird)

    def test_wings_start_on_downstroke_not_every_update(self):
        self.update(0.)
        self.update(.249)
        self.assertEqual(self.mixer.events, [])
        self.update(.25)
        self.update(.3)
        self.assertEqual([event[0] for event in self.mixer.events], ['wing_flap'])
        self.walk_to(.73)
        self.assertEqual([event[0] for event in self.mixer.events], ['wing_flap']*2)
        self.assertTrue(all(event[2] == 0 for event in self.mixer.events))

    def test_animation_manifest_controls_sound_contact_time(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'bird.json'
            path.write_text(json.dumps({'loops':{'flap_north':[
                {'duration_ms':value} for value in (100,100,200,100,100)]}}))
            self.audio = RegentAerialAudio(self.game, mixer=self.mixer, bird_manifest=path)
            self.update(0.)
            self.update(.25)
            self.assertEqual(self.mixer.events, [])
            self.update(.4)
            self.assertEqual(self.mixer.events[0][0], 'wing_flap')

    def test_bank_and_glide_suppress_wings_but_allow_a_visible_hawk_call(self):
        self.update(0.)
        self.walk_to(CALL_TIMES[0]+.05, bank=-20.)
        self.assertEqual([event[0] for event in self.mixer.events], ['hawk_call'])
        self.walk_to(3., flapping=False)
        self.assertEqual([event[0] for event in self.mixer.events], ['hawk_call'])

    def test_wingbeat_mix_is_quieter_than_the_call_and_obeys_effects_gain(self):
        self.game.audio.set_effects(.5)
        self.update(0.)
        self.walk_to(CALL_TIMES[0]+.1)
        calls = [gain for name,gain,_ in self.mixer.events if name == 'hawk_call']
        wings = [gain for name,gain,_ in self.mixer.events if name == 'wing_flap']
        self.assertEqual(calls, [GAINS['hawk_call']*.5])
        self.assertTrue(wings)
        self.assertTrue(all(gain == GAINS['wing_flap']*.5 < calls[0] for gain in wings))

    def test_muting_stops_owned_sound_and_unmuting_cannot_replay_missed_cues(self):
        self.update(0.)
        self.update(.25)
        self.assertTrue(self.audio.voices)
        self.game.audio.set_effects(0)
        self.assertFalse(self.audio.voices)
        self.walk_to(CALL_TIMES[0]+.1)
        before = len(self.mixer.events)
        self.game.audio.set_effects(1)
        self.update(CALL_TIMES[0]+.11)
        self.assertEqual(len(self.mixer.events), before)

    def test_pause_freezes_cues_and_unpauses_only_owned_channels(self):
        self.update(0.)
        self.update(.25)
        voice = self.audio.voices['wing_flap']
        self.audio.update(3., self.snapshot(3.25), paused=True)
        self.assertTrue(voice.channel.paused)
        self.assertEqual(self.audio._last_seconds, .25)
        self.assertEqual(len(self.mixer.events), 1)
        self.audio.update(0., self.snapshot(.25), paused=False)
        self.assertFalse(voice.channel.paused)
        self.assertEqual(len(self.mixer.events), 1)

    def test_reused_channel_is_never_modified_or_stopped(self):
        self.update(0.)
        self.update(.25)
        channel = self.audio.voices['wing_flap'].channel
        foreign = object()
        channel.sound = foreign
        before = (channel.stops, channel.volume_changes)
        self.audio.update(.05, self.snapshot(.3), paused=True)
        self.audio.stop()
        self.assertIs(channel.sound, foreign)
        self.assertEqual((channel.stops,channel.volume_changes), before)
        self.assertFalse(channel.paused)

    def test_long_frame_discards_backlog_and_all_cues_are_finite(self):
        self.update(0.)
        self.update(.25)
        self.update(CALL_TIMES[-1]+.02)
        self.assertEqual([event[0] for event in self.mixer.events], ['wing_flap'])
        self.assertFalse(self.audio.voices)
        self.update(CALL_TIMES[-1]+.03)
        self.assertEqual(len(self.mixer.events), 1)

    def test_offscreen_hidden_and_end_of_aerial_release_voices_without_music(self):
        for hidden in ({'screen_xy':[900,160]}, {'visible':False}):
            with self.subTest(hidden=hidden):
                self.audio.reset()
                self.update(0.)
                self.update(.25)
                self.update(.3, **hidden)
                self.assertFalse(self.audio.voices)
        self.audio.reset();self.update(0.);self.update(.25)
        snapshot = self.snapshot(.3);snapshot['ground_handoff'] = True
        self.audio.update(.05,snapshot)
        self.assertFalse(self.audio.voices)
        self.audio.reset();self.update(0.);self.update(.25)
        self.audio.update(0.,None)
        self.assertFalse(self.audio.voices)
        self.mixer.music.assert_not_called()
        self.mixer.stop.assert_not_called()

    def test_no_mixer_or_busy_channels_fail_quietly_without_stealing(self):
        self.mixer.ready = False
        self.update(0.);self.update(.25)
        self.mixer.Sound.assert_not_called()
        self.mixer.ready = True
        for channel in self.mixer.channels:channel.sound = object()
        self.walk_to(.73)
        self.assertEqual(self.mixer.events, [])
        self.assertTrue(all(channel.stops == 0 for channel in self.mixer.channels))

    def test_reset_restarts_the_cue_timeline_for_a_new_gallery_playback(self):
        self.update(0.);self.update(.25)
        self.audio.reset()
        self.assertFalse(self.audio.voices)
        self.update(0.);self.update(.25)
        self.assertEqual([event[0] for event in self.mixer.events], ['wing_flap']*2)


class RegentAerialSampleTests(unittest.TestCase):
    def setUp(self):
        pygame.mixer.init(frequency=48000, size=-16, channels=2)
        self.addCleanup(pygame.mixer.quit)

    def test_recordings_decode_and_the_actual_wing_mix_is_quieter(self):
        levels = {}
        for name, limit in (('hawk_call', 2.), ('wing_flap', .35)):
            with self.subTest(cue=name):
                sound = pygame.mixer.Sound(str(ASSETS/(name+'.ogg')))
                self.assertGreater(sound.get_length(), .1)
                self.assertLessEqual(sound.get_length(), limit)
                pcm = array('h', sound.get_raw())
                peak = max(abs(sample) for sample in pcm)/32768
                self.assertGreater(peak, .2)
                self.assertLess(peak, .6)
                levels[name] = math.sqrt(sum(sample*sample for sample in pcm)/len(pcm))/32768
        self.assertLess(levels['wing_flap']*GAINS['wing_flap'],
                        levels['hawk_call']*GAINS['hawk_call']*.35)

    def test_native_playback_uses_effects_volume_and_mute_releases_the_voice(self):
        game = SimpleNamespace(audio=AudioSettings(None))
        audio = RegentAerialAudio(game)
        self.addCleanup(audio.stop)
        snapshot = lambda t: {'seconds':t, 'bird':{'screen_xy':[240,160], 'bank':0}}
        game.audio.set_effects(.5)
        audio.update(0.,snapshot(0.))
        audio.update(.25,snapshot(.25))
        voice = audio.voices['wing_flap']
        self.assertIs(voice.channel.get_sound(), voice.sound)
        self.assertAlmostEqual(voice.channel.get_volume(), GAINS['wing_flap']*.5, delta=1/128)
        game.audio.set_effects(0)
        self.assertFalse(audio.voices)
        self.assertIsNone(voice.channel.get_sound())


if __name__ == '__main__':unittest.main()
