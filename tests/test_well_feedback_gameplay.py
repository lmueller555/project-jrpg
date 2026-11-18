"""Actual-Game examination and short-radius well sound integration.

Material synthesis and channel failure/lease rules have separate focused unit
coverage. These cases exercise the production Game hooks and real work clock.
"""
from copy import deepcopy
import math
from unittest.mock import patch

import pygame

from well_live_test_support import LiveWellCase


class Channel:
    def __init__(self):
        self.sound = None
        self.gain = 0.
        self.stops = 0

    def get_sound(self):return self.sound
    def get_busy(self):return self.sound is not None
    def set_volume(self, gain):self.gain = gain
    def play(self, sound, **kwargs):self.sound = sound
    def stop(self):
        self.stops += 1
        self.sound = None


class WellFeedbackGameplay(LiveWellCase):
    def setUp(self):
        super().setUp()
        from gardener_well_runtime import Gardener as IntegratedGardener
        from npc_routines import Gardener as PublicGardener
        self.assertIs(PublicGardener, IntegratedGardener,
                      'The public actor binding must retain the controller-driven routine')
        self.assertIsInstance(self.actor, IntegratedGardener)
        self.game.opening_fade = self.game.transfer_cooldown = 0.
        self.audio = self.game.well_audio
        self.examination = self.game.well_examination
        self.channels, self.heard = [], []
        self.sounds = {}

        def channel():
            result = Channel()
            self.channels.append(result)
            return result

        def sound(name):
            return self.sounds.setdefault(name, object())

        self.addCleanup(patch.stopall)
        patch('pygame.mixer.find_channel', side_effect=channel).start()
        patch.object(self.audio, '_sound', side_effect=sound).start()
        self.audio.observer = lambda action, key, **data: self.heard.append(
            {'action': action, 'key': key, **data})

    def tearDown(self):
        self.audio.stop()
        super().tearDown()

    def listen_near(self):
        # Stay beside the well so the listener never blocks its loading route.
        self.game.player.position.update(492, 864)
        self.game.player.facing = 'right'
        self.game.update(0, (0, 0), False)

    @staticmethod
    def key(repeat=False):
        return pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e, repeat=repeat)

    def starts(self, sound=None, ambient=None):
        return [event for event in self.heard if event['action'] == 'start'
                and (sound is None or event['sound'] == sound)
                and (ambient is None or event['ambient'] is ambient)]

    def close_prose(self):
        for _ in range(20):
            if not self.game.social.active:return
            self.game.social.advance()
        self.fail('Well inspection did not finish')

    def test_real_e_input_opens_repeatable_idle_text_without_work_or_rewards(self):
        self.listen_near()
        before = self.signature()
        inventory = deepcopy(self.game.inventory.to_dict())
        flags = set(self.game.social.flags)
        self.assertEqual(self.examination.interaction_hint(), 'E: Examine well')
        self.game.handle_events([self.key(), self.key()])
        self.assertEqual(self.game.social.script_identifier, 'well_examine_idle')
        self.assertEqual(self.game.social.page_index, 0)
        self.assertEqual(self.signature(), before)
        self.close_prose()
        self.assertEqual(self.game.inventory.to_dict(), inventory)
        self.assertEqual(self.game.social.flags, flags)
        self.game.handle_events([self.key(repeat=True)])
        self.assertFalse(self.game.social.active)
        self.game.handle_events([self.key()])
        self.assertEqual(self.game.social.script_identifier, 'well_examine_idle')
        self.assertIsNone(self.well.owner)

    def test_active_examination_holds_and_resumes_same_pail_operation(self):
        self.to_phase('lower')
        self.listen_near()
        before = self.signature()
        self.assertTrue(self.audio.voices)
        self.game.handle_events([self.key()])
        self.assertEqual(self.game.social.script_identifier, 'well_examine_working')
        self.game.update(2, (0, 0), False)
        self.assertEqual(self.signature(), before)
        self.assertEqual(self.actor.pail_location, 'well')
        self.assertFalse(self.audio.voices)
        self.close_prose()
        self.game.update(1/60, (0, 0), False)
        self.assertEqual(self.well.snapshot().operation_id, before[0]['operation_id'])
        self.assertGreater(self.well.snapshot().phase_elapsed_ms,
                           before[0]['phase_elapsed_ms'])
        self.assertIs(self.well.owner, self.actor)

    def test_examination_respects_facing_distance_scene_and_higher_priority_action(self):
        self.listen_near()
        self.game.player.facing = 'front'
        self.assertFalse(self.examination.available())
        self.game.player.facing = 'back'
        self.game.player.position.update(528, 960)
        self.assertFalse(self.examination.available())
        self.listen_near()
        with patch.object(self.game.services, 'interact', return_value=True), \
                patch.object(self.examination, 'interact', wraps=self.examination.interact) as examine:
            self.game.handle_events([self.key()])
            examine.assert_not_called()
        door = next(door for door in self.world.doors if door.data['id'] == 'home_a')
        self.assertTrue(self.game.enter(door))
        self.assertFalse(self.examination.available())
        self.assertEqual(self.examination.interaction_hint(), '')

    def test_actual_voices_fall_off_quickly_and_stop_at_eighty_units(self):
        self.to_phase('lower')
        self.listen_near()
        source = next(voice[0] for voice in self.audio.voices.values()
                      if voice[0].sound == 'well_winding')
        gains = []
        for distance, multiplier in ((32, 1.), (48, 8/27), (64, 1/27)):
            self.game.player.position.update(528, 864+distance)
            self.game.update(0, (0, 0), False)
            gain = self.audio._gain(source)
            self.assertAlmostEqual(gain, source.gain*self.game.audio.effects_volume*multiplier)
            voice = self.audio.voices[source.key]
            self.assertAlmostEqual(voice[1].gain, gain,
                                   'Game updates must apply attenuation to the leased channel')
            gains.append(gain)
        self.assertLess(gains[-1], gains[0]*.04)
        self.native(camera=(0, 0))
        self.audio.refresh_volume()
        self.assertAlmostEqual(self.audio._gain(source), gains[-1])
        self.game.player.position.update(528, 944)
        self.game.update(0, (0, 0), False)
        self.assertEqual(self.audio._gain(source), 0.)
        self.assertFalse(self.audio.voices)

    def test_actual_operation_emits_contacts_once_and_draws_emit_nothing(self):
        self.listen_near()
        self.to_phase('lower')
        self.until(lambda: self.well.snapshot().completed)
        contacts = self.starts(ambient=False)
        self.assertEqual([event['sound'] for event in contacts],
                         ['well_hook', 'well_splash', 'well_drip', 'well_hook'])
        self.assertEqual(len({event['key'] for event in contacts}), len(contacts))
        before, count = self.signature(), len(self.heard)
        for _ in range(5):self.native()
        self.assertEqual(self.signature(), before)
        self.assertEqual(len(self.heard), count)

    def test_muted_and_distant_contacts_are_consumed_without_replay(self):
        for mode in ('muted', 'distant'):
            with self.subTest(mode=mode):
                self.actor.reset_cycle()
                self.audio.reset()
                self.heard.clear()
                self.game.player.position.update((528, 1000) if mode == 'distant' else (492, 864))
                self.game.player.facing = 'right'
                self.game.audio.set_effects(0 if mode == 'muted' else 1)
                self.to_phase('await_operator')
                self.assertTrue(any(event.cue_id == 'attached' for event in self.actor.well_events))
                self.assertFalse(self.starts(ambient=False))
                self.game.audio.set_effects(1)
                self.listen_near()
                self.game.update(.1, (0, 0), False)
                self.assertFalse(self.starts(ambient=False))

    def test_long_frame_discards_stale_contacts_instead_of_bursting_after_hitch(self):
        self.listen_near()
        self.to_phase('attach')
        self.heard.clear()
        self.game.update(6, (0, 0), False)
        self.assertTrue(self.actor.well_events)
        self.assertFalse(self.starts(ambient=False))
        self.assertIn(self.well.snapshot().phase_id, ('lower', 'fill'))

    def test_pause_focus_journal_and_map_release_voices_without_advancing_work(self):
        self.to_phase('lower')
        self.listen_near()
        for owner, flag, blocked, restored in (
                (self.game.pause, 'is_open', True, False),
                (self.game, '_music_focused', False, True),
                (self.game, 'map_open', True, False),
                (self.game.quest_ui, 'journal_open', True, False)):
            with self.subTest(flag=flag):
                self.game.update(0, (0, 0), False)
                self.assertTrue(self.audio.voices)
                before = self.signature()
                setattr(owner, flag, blocked)
                self.game.update(.5, (0, 0), False)
                self.assertEqual(self.signature(), before)
                self.assertFalse(self.audio.voices)
                setattr(owner, flag, restored)
        self.game.update(0, (0, 0), False)
        self.assertTrue(self.audio.voices)

    def test_interior_work_is_silent_and_return_has_no_old_contacts(self):
        self.to_phase('lower')
        self.listen_near()
        door = next(door for door in self.world.doors if door.data['id'] == 'home_a')
        self.assertTrue(self.game.enter(door))
        self.heard.clear()
        self.game.update(8, (0, 0), False)
        self.assertFalse(self.audio.voices)
        self.assertFalse(self.starts())
        self.assertTrue(self.game.enter(self.game.world.doors[0]))
        self.listen_near()
        self.assertFalse(self.starts(ambient=False))
        self.assertIs(self.well.owner, self.actor)

    def test_pour_sound_is_once_at_actual_flow_and_local_to_the_gardener(self):
        self.start_trip()
        self.until(lambda: self.actor.state.startswith('water_'))
        self.heard.clear()
        self.game.player.position.update(self.actor.position+(0, 30))
        self.until(lambda: bool(self.starts('well_pour')), limit=3)
        self.assertEqual(self.actor.presentation_selection()['effect'], 'pour')
        self.assertEqual(len(self.starts('well_pour')), 1)
        source = next(voice[0] for voice in self.audio.voices.values()
                      if voice[0].sound == 'well_pour')
        self.assertLess(math.dist(source.point(), self.actor.position), .01)
        self.game.update(.1, (0, 0), False)
        self.assertEqual(len(self.starts('well_pour')), 1)
        self.game.player.position.update(528, 900)
        self.game.update(0, (0, 0), False)
        self.assertEqual(self.audio._gain(source), 0.)
        self.assertFalse(any(voice[0].sound == 'well_pour' for voice in self.audio.voices.values()))

    def test_continue_and_title_clear_audio_handles_without_serializing_them(self):
        self.to_phase('lower')
        self.listen_near()
        self.assertTrue(self.audio.voices)
        payload = self.game.journey_snapshot()
        self.assertNotIn('well_audio', payload)
        self.game.saved_journey = deepcopy(payload)
        self.assertTrue(self.game.begin_journey(True))
        self.assertFalse(self.audio.voices)
        self.assertEqual(self.actor.state, 'rest')
        self.assertEqual(self.well.snapshot().phase_id, 'idle')
        self.game.return_to_title()
        self.assertFalse(self.audio.voices)


if __name__ == '__main__':
    import unittest
    unittest.main()
