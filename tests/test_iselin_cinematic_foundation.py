"""Additive action fixtures exercise the actual arrival and Gallery owners."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame

from cinematic_actor_actions import load_actions
from main import Game
from regent_arrival import RegentArrival
from test_cinematic_actor_actions import MANIFEST, probe_action
from test_mill_battle_gameplay import click, key
from test_regent_arrival import acknowledge_report, seed_mill_report

class IselinCinematicFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The expensive production world is shared; each case starts a fresh
        # pending arrival receipt through its normal controller boundary.
        cls.directory = tempfile.TemporaryDirectory(prefix='iselin-action-runtime-')
        cls.folder = Path(cls.directory.name)
        cls.path = cls.folder/'journey.json'
        cls.game = Game(fullscreen=False, start_on_title=False, window_size=(960, 640),
                        save_path=cls.path, settings_path=cls.folder/'settings.json')
        cls.game.audio.set_music(0);cls.game.audio.set_effects(0)
        seed_mill_report(cls.game)
        acknowledge_report(cls.game)
        cls.game.update(.05, (0, 0), False)
        if not cls.game.regent_arrival.active:raise AssertionError('Real arrival did not start')
        cls.game.regent_arrival._load()

    @classmethod
    def tearDownClass(cls):
        if cls.game.gallery_session is not None:cls.game.gallery_session.close()
        cls.game.regent_arrival.reset()
        cls.game.opening_audio.reset();cls.game.regional_audio.reset();cls.game.music.stop()
        pygame.quit()
        cls.directory.cleanup()

    @staticmethod
    def install_action(scene):
        scene._load()
        record = json.loads(MANIFEST.read_text())
        record['actions'] = {'probe': probe_action()}
        # Compile the additive fixture with the real loader and approved poses;
        # neither the manifest nor any production method is monkeypatched.
        art = scene.actor_art['iselin']
        art['actions'] = load_actions(record, art['poses'], MANIFEST)

    def setUp(self):
        self.g = self.game
        self.g.on_title = False;self.g.on_gallery = False;self.g._music_focused = True
        self.g.pause.close();self.g.social.cancel_script()
        self.scene = self.g.regent_arrival
        self.assertTrue(self.scene.restore({'version': 1, 'state': 'pending'}))
        self.assertTrue(self.scene.maybe_start())
        self.install_action(self.scene)
        self.station(self.scene)
        pygame.event.clear()

    @staticmethod
    def station(scene):
        # An authored shot containing Iselin and player-held dialogue prevents
        # an automatic shot change from hiding action lifecycle assertions.
        scene.phase_index = next(i for i, phase in enumerate(scene.data['phases'])
                                 if phase['id'] == 'gate_greeting')
        scene.phase_time = 0.
        scene.dialogue_index = scene.page_index = 0

    def play(self, scene=None, cue='fixture-cue'):
        scene = self.scene if scene is None else scene
        self.assertTrue(scene.play_actor_action('iselin', 'probe', cue))
        return next(actor for actor in scene.phase['actors'] if actor['id'] == 'iselin')

    def assert_cleared(self, scene=None):
        scene = self.scene if scene is None else scene
        state = scene.actor_action_state('iselin')
        self.assertEqual(state['stage'], 'idle')
        self.assertIsNone(state['action'])
        self.assertIsNone(state['cue_id'])
        self.assertFalse(state['active'])

    def test_actual_game_updates_action_frames_and_holds_rest_until_another_cue(self):
        actor = self.play()
        poses = self.scene.actor_art['iselin']['poses']
        self.assertIs(self.scene._frame(actor), poses['stand_left'])
        self.g.update(.1, (0, 0), False)
        self.assertIs(self.scene._frame(actor), poses['turn_left_back'])
        self.g.update(.2, (0, 0), False)
        self.assertIs(self.scene._frame(actor), poses['listen_left'])
        self.assertTrue(self.scene.release_actor_action('iselin', 'fixture-cue'))
        self.g.update(.12, (0, 0), False)
        self.assertIs(self.scene._frame(actor), poses['stand_right'])
        self.g.update(.08, (0, 0), False)
        self.assertEqual(self.scene.actor_action_state('iselin')['stage'], 'rest')
        self.assertIs(self.scene._frame(actor), poses['stand_back'])
        self.g.update(.3, (0, 0), False)
        self.assertIs(self.scene._frame(actor), poses['stand_back'])
        self.assertFalse(self.scene.play_actor_action('iselin', 'probe', 'fixture-cue'))
        self.assertTrue(self.scene.play_actor_action('iselin', 'probe', 'later-cue'))
        self.assertIs(self.scene._frame(actor), poses['stand_left'])

    def test_pause_and_both_focus_guards_freeze_action_and_scene_together(self):
        self.play();self.g.update(.05, (0, 0), False)
        def clock():
            return (self.scene.actor_action_state('iselin'), self.scene.phase_time, self.scene.elapsed)
        before = clock()
        key(self.g, pygame.K_ESCAPE)
        self.assertTrue(self.scene.paused)
        self.g.update(.4, (0, 0), False)
        self.assertEqual(clock(), before)
        key(self.g, pygame.K_ESCAPE)
        self.g.handle_events([pygame.event.Event(pygame.WINDOWFOCUSLOST)])
        self.assertFalse(self.scene.focused)
        self.g.update(.4, (0, 0), False)
        self.assertEqual(clock(), before)
        self.g.handle_events([pygame.event.Event(pygame.WINDOWFOCUSGAINED)])
        self.g._music_focused = False
        self.g.update(.4, (0, 0), False)
        self.assertEqual(clock(), before)
        self.g._music_focused = True
        self.g.update(.025, (0, 0), False)
        self.assertGreater(self.scene.actor_action_state('iselin')['elapsed_ms'], before[0]['elapsed_ms'])

    def test_repeated_real_draws_do_not_start_advance_or_repeat_action_cues(self):
        actor = self.play();self.g.update(.125, (0, 0), False)
        before = (self.scene.actor_action_state('iselin'), self.scene.phase_time,
                  self.scene.elapsed, self.scene.dialogue_index)
        image = pygame.image.tobytes(self.scene._frame(actor), 'RGBA')
        for _ in range(3):
            self.g.draw()
            self.assertEqual((self.scene.actor_action_state('iselin'), self.scene.phase_time,
                              self.scene.elapsed, self.scene.dialogue_index), before)
            self.assertEqual(pygame.image.tobytes(self.scene._frame(actor), 'RGBA'), image)
        self.assertFalse(self.scene.play_actor_action('iselin', 'probe', 'fixture-cue'))

    def test_authored_phase_transition_clears_player_and_cue_ledger(self):
        self.play()
        self.scene.dialogue_index = len(self.scene.phase['dialogue'])
        self.g.update(self.scene.phase['min_seconds']+.001, (0, 0), False)
        self.assertEqual(self.scene.shot, 'gate_admission')
        self.assert_cleared()
        self.assertTrue(self.scene.play_actor_action('iselin', 'probe', 'fixture-cue'))

    def test_reset_restore_and_new_start_remove_every_transient_action(self):
        for operation in ('reset', 'restore'):
            with self.subTest(operation=operation):
                self.play()
                self.g.update(.15, (0, 0), False)
                if operation == 'reset':self.scene.reset()
                else:self.assertTrue(self.scene.restore({'version': 1, 'state': 'pending'}))
                self.assert_cleared()
                self.assertFalse(self.scene.play_actor_action('iselin', 'probe', 'inactive-cue'))
                self.assertTrue(self.scene.restore({'version': 1, 'state': 'pending'}))
                self.assertTrue(self.scene.maybe_start())
                self.assert_cleared()
                self.station(self.scene)
        self.play()

    def test_rejected_restore_keeps_active_action_and_existing_receipt_unchanged(self):
        actor = self.play();self.g.update(.125, (0, 0), False)
        before = (self.scene.actor_action_state('iselin'), self.scene.to_dict(),
                  self.scene.phase_index, self.scene.phase_time, self.scene.elapsed,
                  self.scene.active, self.scene._frame(actor))
        for invalid in ({'version': 2, 'state': 'pending'}, {'version': 1, 'state': 'unknown'}):
            with self.subTest(snapshot=invalid):
                self.assertFalse(self.scene.restore(invalid))
                self.assertEqual((self.scene.actor_action_state('iselin'), self.scene.to_dict(),
                                  self.scene.phase_index, self.scene.phase_time, self.scene.elapsed,
                                  self.scene.active, self.scene._frame(actor)), before)

    def test_normal_finish_and_skip_clear_actions_without_changing_quest_rewards(self):
        for reason in ('finished', 'skipped'):
            with self.subTest(reason=reason):
                before = (deepcopy(self.g.inventory.to_dict()), deepcopy(self.g.quests.to_dict()),
                          deepcopy(self.g.battle_rewards.to_dict()))
                self.play()
                if reason == 'skipped':click(self.g, self.scene.skip_rect.center)
                else:self.assertTrue(self.scene.finish('finished'))
                self.assert_cleared()
                self.assertEqual(self.scene.to_dict(), {'version': 1, 'state': 'seen'})
                self.assertFalse(self.scene.finish(reason))
                self.assertEqual((self.g.inventory.to_dict(), self.g.quests.to_dict(),
                                  self.g.battle_rewards.to_dict()), before)
                saved = json.loads(self.path.read_text())
                self.assertEqual(saved['regent_arrival'], {'version': 1, 'state': 'seen'})
                self.assertTrue(RegentArrival.valid_journey(saved))
                self.assertTrue(self.scene.restore({'version': 1, 'state': 'pending'}))
                self.assertTrue(self.scene.maybe_start());self.station(self.scene)

    def test_pending_save_continue_restarts_scene_without_persisting_action_state(self):
        self.assertTrue(self.g.save_progress())
        before = deepcopy(self.g.journey_snapshot())
        self.play();self.g.update(.125, (0, 0), False)
        self.assertTrue(self.g.save_progress())
        payload = json.loads(self.path.read_text())
        expected = deepcopy(before)
        expected['save_context']['playtime'] += .125
        self.assertEqual(payload, expected)
        self.assertEqual(payload['regent_arrival'], {'version': 1, 'state': 'pending'})
        self.assertTrue(RegentArrival.valid_journey(payload))
        self.g.on_title = True
        self.assertTrue(self.g.begin_journey(True), self.g.save_error)
        self.assertTrue(self.scene.active)
        self.assertEqual(self.scene.shot, 'sanctuary_close')
        self.assertEqual(self.scene.phase_time, 0)
        self.assert_cleared()
        self.assertEqual(self.g.inventory.to_dict(), before['inventory'])
        self.assertEqual(self.g.quests.to_dict(), before['quests'])

    def test_legacy_static_and_loop_frames_keep_their_existing_selection(self):
        art = self.scene.actor_art['iselin']
        static = {'id': 'iselin', 'pose': 'listen_left', 'position': [400, 300]}
        walking = {'id': 'iselin', 'pose': 'walk_back', 'position': [400, 300]}
        for seconds, index in ((0, 0), (.035, 1), (.105001, 3), (.559, 15), (.560001, 0)):
            with self.subTest(seconds=seconds):
                self.scene.phase_time = seconds
                self.assertIs(self.scene._frame(static), art['poses']['listen_left'])
                self.assertIs(self.scene._frame(walking), art['loops']['walk_back'][index][0])
        self.play()
        self.scene.clear_actor_actions()
        self.assert_cleared()
        self.assertIs(self.scene._frame(static), art['poses']['listen_left'])

    def test_only_active_current_shot_actors_can_receive_an_action(self):
        self.scene.phase_index = 0
        self.assertFalse(self.scene.play_actor_action('iselin', 'probe', 'offscreen-cue'))
        self.assert_cleared()
        self.station(self.scene)
        self.assertFalse(self.scene.play_actor_action('missing-actor', 'probe', 'unknown-cue'))
        self.assertFalse(self.scene.release_actor_action('iselin'))
        self.play()

    def test_gallery_close_clears_discarded_child_and_keeps_parent_save_bytes(self):
        self.scene.reset()
        self.g.on_title = False
        self.assertTrue(self.g.save_progress())
        raw = self.path.read_bytes()
        parent = (self.g.world, tuple(self.g.player.position), deepcopy(self.g.quests.to_dict()),
                  deepcopy(self.g.inventory.to_dict()), deepcopy(self.g.saved_journey))
        self.g.on_title = True
        self.assertTrue(self.g.open_gallery())
        self.assertTrue(self.g.launch_gallery_scene('regent_arrival'))
        session = self.g.gallery_session
        try:
            child_scene = session.game.regent_arrival
            self.install_action(child_scene);self.station(child_scene)
            self.play(child_scene)
            session.update(.125)
            self.assertEqual(child_scene.actor_action_state('iselin')['stage'], 'entry')
            self.assertFalse(session.game.save_progress())
            session.close()
            self.assert_cleared(child_scene)
            session.close()
            self.assertIsNone(self.g.gallery_session)
            self.assertEqual(self.path.read_bytes(), raw)
            self.assertEqual((self.g.world, tuple(self.g.player.position), self.g.quests.to_dict(),
                              self.g.inventory.to_dict(), self.g.saved_journey), parent)
        finally:
            session.close();self.g.close_gallery();self.g.on_title = False


if __name__ == '__main__':unittest.main()
