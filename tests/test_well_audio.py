"""Short-radius well mixing, ownership and discarded-cue regressions."""
from collections import deque
from types import SimpleNamespace as NS
from unittest import TestCase, mock
import os

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import pygame

from audio_settings import AudioSettings
from regional_audio import Source, distance_gain
from well_audio import WellAudio, WELL_POSITION, well_distance_gain
from well_audio_samples import DURATIONS, samples


class Channel:
    def __init__(self):
        self.sound = None; self.gain = 0.; self.stops = 0

    def get_sound(self): return self.sound
    def set_volume(self, gain): self.gain = gain
    def play(self, sound, **kwargs): self.sound = sound
    def stop(self): self.stops += 1; self.sound = None


class WellAudioTests(TestCase):
    def setUp(self):
        self.state = NS(operation_id=1, total_elapsed_ms=0., phase_id='idle',
                        pail_owner='actor', required_station=None,
                        crank_direction=0, mouth_submerged=False)
        self.selection = {'effect': None}
        self.actor = NS(data={'id': 'sanctuary_gardener'},
                        well_snapshot=self.state, well_events=deque(),
                        presentation_selection=lambda: dict(self.selection),
                        state='rest', water_units=0, pail_location='rest',
                        completed_cycles=0, step_index=0, state_ms=0., POUR_MS=2400,
                        position=pygame.Vector2(322, 350))
        town = NS(npcs=[self.actor])
        self.game = NS(town=town, world=town, audio=AudioSettings(None),
                       player=NS(position=pygame.Vector2(492, 864)),
                       on_title=False, _music_focused=True)
        self.audio = WellAudio(self.game)
        self.channels = []
        def lease():
            channel = Channel(); self.channels.append(channel); return channel
        self.addCleanup(mock.patch.stopall)
        mock.patch('pygame.mixer.find_channel', side_effect=lease).start()
        self.sound_patch = mock.patch.object(self.audio, '_sound', side_effect=lambda name: object())
        self.sound_patch.start()
        self.observations = []
        self.audio.observer = lambda action, key, **data: self.observations.append((action, key, data))

    def source(self, key='test', **kwargs):
        return Source(key, 'well_hook', 'well.metal', WELL_POSITION,
                      near=32, far=80, **kwargs)

    def event(self, cue='attached', operation=1, milliseconds=0):
        event = NS(event_id=(operation, cue), operation_id=operation,
                   cue_id=cue, operation_elapsed_ms=milliseconds)
        self.actor.well_events.append(event)
        return event

    def winding(self):
        self.state.phase_id = 'lower'; self.state.pail_owner = 'well'
        self.state.crank_direction = 1

    def starts(self):
        return [entry for entry in self.observations if entry[0] == 'start']

    def test_steep_cubic_gain_and_exact_short_cutoff(self):
        for distance, expected in ((0, 1), (32, 1), (48, 8/27), (64, 1/27), (80, 0), (100, 0)):
            self.assertAlmostEqual(well_distance_gain(distance), expected)
        self.assertGreater(well_distance_gain(79.99), 0)
        self.assertEqual(distance_gain(60, 20, 100), .5,
                         'The wider regional attenuation stays unchanged')

    def test_listener_position_and_effects_slider_control_gain_not_camera(self):
        source = self.source()
        self.game.player.position.update(480, 864)
        self.assertTrue(self.audio.play(source))
        channel = self.channels[-1]
        self.assertAlmostEqual(channel.gain, .5*8/27)
        self.game.camera = NS(position=(9999, 9999))
        self.game.audio.set_effects(.5)
        self.assertAlmostEqual(channel.gain, .25*8/27)
        self.game.player.position.update(448, 864)
        self.audio.refresh_volume()
        self.assertFalse(self.audio.voices)

    def test_idle_is_silent_and_current_work_beds_follow_phase(self):
        self.audio.update(.1)
        self.assertFalse(self.audio.voices)
        self.winding(); self.audio.update(.1)
        self.assertEqual(set(self.audio.voices), {'well.winding'})
        self.state.phase_id = 'fill'; self.state.crank_direction = 0
        self.state.mouth_submerged = True
        self.audio.update(.1)
        self.assertEqual(set(self.audio.voices), {'well.filling'})
        self.state.phase_id = 'await_retrieval'; self.state.required_station = 'loading'
        self.audio.update(.1)
        self.assertFalse(self.audio.voices)

    def test_events_are_read_once_without_draining_gameplay_observations(self):
        event = self.event()
        self.actor.well_events.append(event)
        before = list(self.actor.well_events)
        for _ in range(10): self.audio.update(0)
        self.assertEqual(len(self.starts()), 1)
        self.assertEqual(list(self.actor.well_events), before)
        self.audio.update(1)
        self.audio.update(0)
        self.assertEqual(len(self.starts()), 1)

    def test_offscreen_muted_and_distant_events_never_replay(self):
        for condition in ('offscreen', 'mute', 'distance'):
            with self.subTest(condition=condition):
                self.audio.reset(); self.actor.well_events.clear(); self.observations.clear()
                self.event()
                if condition == 'offscreen': self.game.world = NS()
                elif condition == 'mute': self.game.audio.set_effects(0)
                else: self.game.player.position.update(448, 864)
                self.audio.update(.01)
                self.game.world = self.game.town; self.game.audio.set_effects(1)
                self.game.player.position.update(492, 864)
                self.audio.update(0)
                self.assertFalse(self.starts())

    def test_hitch_and_old_operation_impacts_are_discarded(self):
        self.event('attached', milliseconds=0)
        self.state.total_elapsed_ms = 1000
        self.audio.update(0)
        self.assertFalse(self.starts())
        self.state.total_elapsed_ms = 0
        self.audio.update(0)
        self.assertFalse(self.starts(), 'An old contact cannot become new after a clock change')
        self.event('water_contact', operation=0)
        self.audio.update(0)
        self.assertFalse(self.starts())

    def test_recent_contact_accepts_normal_frame_latency(self):
        self.event('water_contact', milliseconds=50)
        self.state.total_elapsed_ms = 150
        self.audio.update(0)
        self.assertEqual([x[2]['sound'] for x in self.starts()], ['well_splash'])

    def test_new_contact_is_not_aged_by_the_call_that_observes_it(self):
        self.event()
        self.audio.update(1)
        self.assertIn('well.1.attached', self.audio.voices)
        self.assertEqual(self.audio.voices['well.1.attached'][3], 0.)
        self.audio.update(.22)
        self.assertNotIn('well.1.attached', self.audio.voices)

    def test_pour_fires_once_at_visible_flow_and_stops_with_it(self):
        self.actor.state = 'water_west_flowers'; self.actor.water_units = 6
        self.actor.pail_location = 'actor'; self.actor.step_index = 8
        self.actor.state_ms = 920; self.selection['effect'] = 'pour'
        self.game.player.position.update(322, 390)
        self.audio.update(0)
        self.assertEqual([x[2]['sound'] for x in self.starts()], ['well_pour'])
        self.assertFalse(self.starts()[0][2]['ambient'])
        self.audio.update(.1)
        self.selection['effect'] = None; self.audio.update(0)
        self.assertFalse(self.audio.voices)
        self.selection['effect'] = 'pour'; self.audio.update(0)
        self.assertEqual(len(self.starts()), 1)

    def test_empty_or_late_pour_never_invents_water_or_delayed_audio(self):
        self.actor.state = 'water_west_flowers'; self.actor.pail_location = 'actor'
        self.selection['effect'] = 'pour'; self.actor.state_ms = 920
        self.game.player.position.update(322, 390)
        self.audio.update(0)
        self.assertFalse(self.starts())
        self.actor.water_units = 1; self.actor.state_ms = 1300
        self.audio.update(0)
        self.assertFalse(self.starts())
        self.assertEqual(self.actor.water_units, 1)

    def test_pause_and_mute_resume_only_current_ambient_work(self):
        self.winding(); self.event(); self.audio.update(0)
        self.game.pause = NS(is_open=True); self.audio.update(1)
        self.assertFalse(self.audio.voices)
        self.game.pause.is_open = False; self.audio.update(0)
        self.assertEqual(set(self.audio.voices), {'well.winding'})
        hooks = [entry for entry in self.starts() if entry[2]['sound'] == 'well_hook']
        self.assertEqual(len(hooks), 1)
        self.game.audio.set_effects(0)
        self.assertFalse(self.audio.voices)
        self.game.audio.set_effects(1); self.audio.update(0)
        self.assertEqual(set(self.audio.voices), {'well.winding'})

    def test_all_modal_and_session_boundaries_release_owned_voices(self):
        for owner, field in ((self.game, 'on_title'), (self.game, 'map_open'),
                             (self.game, '_is_gallery_preview'), (self.game, 'on_quest_playtest'),
                             (self.game, 'game_over')):
            with self.subTest(field=field):
                self.audio.reset(); self.winding(); self.audio.update(0)
                setattr(owner, field, True); self.audio.update(0)
                self.assertFalse(self.audio.voices)
                setattr(owner, field, False)
        for name, field in (('inventory_ui', 'is_open'), ('services', 'is_open'),
                            ('quest_ui', 'journal_open'), ('social', 'locked'),
                            ('opening', 'locks_player'), ('combat', 'active')):
            self.audio.reset(); self.audio.update(0)
            setattr(self.game, name, NS(**{field: True})); self.audio.update(0)
            self.assertFalse(self.audio.voices)
            setattr(getattr(self.game, name), field, False)

    def test_channel_reuse_never_stops_or_changes_another_owner(self):
        self.audio.play(self.source())
        channel = self.channels[-1]; other = object()
        channel.sound = other; channel.gain = .73
        self.audio.refresh_volume()
        self.assertIs(channel.sound, other)
        self.assertEqual(channel.gain, .73)
        self.assertEqual(channel.stops, 0)

    def test_voice_budget_and_unavailable_channels_do_not_steal(self):
        for index in range(8):
            self.audio.play(self.source(str(index), ambient=index < 4))
        self.assertLessEqual(len(self.audio.voices), 4)
        self.audio.reset(); self.observations.clear(); self.event()
        with mock.patch('pygame.mixer.find_channel', return_value=None):
            self.audio.update(0)
        self.audio.update(0)
        self.assertFalse(self.starts())
        self.assertFalse(self.audio.failed)

    def test_device_failure_is_safe_and_reset_allows_retry(self):
        self.sound_patch.stop()
        with mock.patch('pygame.mixer.get_init', return_value=None):
            self.assertFalse(self.audio.play(self.source()))
        with mock.patch('pygame.mixer.get_init', return_value=(22050, 8, 2)):
            self.assertFalse(self.audio.play(self.source()))
        with mock.patch('pygame.mixer.get_init', side_effect=pygame.error('no device')):
            self.assertFalse(self.audio.play(self.source()))
        self.assertTrue(self.audio.failed)
        self.audio.reset()
        self.assertFalse(self.audio.failed)

    def test_device_loss_while_expiring_a_voice_never_aborts_update(self):
        self.audio.play(self.source())
        channel = self.channels[-1]
        with mock.patch.object(channel, 'stop', side_effect=pygame.error('device closed')):
            self.audio.update(1)
        self.assertTrue(self.audio.failed)
        self.assertFalse(self.audio.voices)

    def test_seen_ids_and_sound_cache_are_bounded(self):
        for index in range(1000): self.audio._remember(('event', index))
        self.assertEqual(len(self.audio._seen), self.audio.SEEN_LIMIT)
        self.sound_patch.stop()
        with mock.patch('pygame.mixer.Sound', side_effect=lambda **kwargs: object()):
            for rate in (8000, 11025, 16000):
                with mock.patch('pygame.mixer.get_init', return_value=(rate, -16, 1)):
                    for name in DURATIONS:
                        self.assertIs(self.audio._sound(name), self.audio._sound(name))
        self.assertEqual(len(self.audio.cache), self.audio.SOUND_CACHE_LIMIT)
        self.assertFalse(any(key[1] == 8000 for key in self.audio.cache))

    def test_prepare_warms_current_bank_without_channels_or_gameplay_events(self):
        self.sound_patch.stop()
        self.event()
        with mock.patch('pygame.mixer.get_init', return_value=(8000, -16, 1)), \
                mock.patch('pygame.mixer.Sound', side_effect=lambda **kwargs: object()) as create, \
                mock.patch('pygame.mixer.find_channel') as channel:
            self.assertTrue(self.audio.prepare())
            self.assertEqual(create.call_count, len(DURATIONS))
            self.assertTrue(self.audio.prepare())
            self.assertEqual(create.call_count, len(DURATIONS))
            channel.assert_not_called()
        self.assertEqual(len(self.audio.cache), len(DURATIONS))
        self.assertFalse(self.audio.voices)
        self.assertFalse(self.audio._seen)
        self.assertEqual(self.audio.clock, 0.)
        self.assertFalse(self.starts())

    def test_prepare_tolerates_missing_device_and_failed_sound_creation(self):
        self.sound_patch.stop()
        with mock.patch('pygame.mixer.get_init', return_value=None):
            self.assertFalse(self.audio.prepare())
        with mock.patch('pygame.mixer.get_init', return_value=(8000, -16, 1)), \
                mock.patch('pygame.mixer.Sound', side_effect=pygame.error('closed')):
            self.assertFalse(self.audio.prepare())
        self.assertTrue(self.audio.failed)
        self.assertFalse(self.audio.voices)

    def test_original_pcm_is_deterministic_distinct_and_leaves_headroom(self):
        fingerprints = set()
        for name, duration in DURATIONS.items():
            pcm = samples(name, 8000, 1)
            self.assertEqual(len(pcm), round(8000*duration))
            self.assertEqual(pcm, samples(name, 8000, 1))
            self.assertGreater(max(abs(value) for value in pcm), 100)
            self.assertLess(max(abs(value) for value in pcm), 10000)
            stereo = samples(name, 8000, 2)
            self.assertEqual(stereo[::2], pcm)
            self.assertEqual(stereo[1::2], pcm)
            fingerprints.add(pcm.tobytes())
        self.assertEqual(len(fingerprints), len(DURATIONS))
