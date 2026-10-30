"""Actual title, village, MQ02 cue and battle ownership of the shared score."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
from main import Game
from quests import MILL_QUEST
from test_mill_battle_gameplay import (
    acknowledge_battle_result, click, finish_mill_battle, key, read_social, seed_completed_mill, seed_mill_handoff, wait_for_spoils,
)


class MusicBattleIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='music-battle-integration-')
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.path = self.directory/'journey.json'
        self.backend = MagicMock()
        self.backend.get_busy.return_value = True
        stream = patch('pygame.mixer.music', self.backend)
        stream.start();self.addCleanup(stream.stop)

    def tearDown(self):pygame.quit()

    def game(self, *, title=False):
        game = Game(window_size=(960, 640), fullscreen=False, start_on_title=title,
                    save_path=self.path, settings_path=self.directory/'settings.json')
        game.audio.set_effects(0)
        pygame.event.clear()
        return game

    def frame(self, game, seconds=0):
        game.update(seconds, (0, 0), False)

    def finish_transition(self, game):
        for _ in range(100):
            if not game.combat.transitioning:return
            self.frame(game, .05)
        self.fail('Battle entry did not reveal the battlefield')

    def seed_encounter(self, game):
        """A valid checkpoint immediately before the new presentation change."""
        seed_mill_handoff(game)
        self.assertTrue(game.accept_quest(MILL_QUEST))
        for objective in ('meet_mira', 'diagnose_mill', 'prepare_journey'):
            self.assertTrue(game.quests.complete_objective(MILL_QUEST, objective))
        quest = game.mill_quest
        record = quest.to_dict()
        record.update(inspected=['mechanism', 'race'], warned=True)
        self.assertTrue(quest.restore(record))
        game.world = quest.upstream
        game.player.position.update(180, 374)
        quest._place_mira(quest.upstream, (156, 374))
        self.assertTrue(game.world.can_stand(game.player.position))
        game.opening_fade = game.transfer_cooldown = 0
        game.camera.reset()
        self.frame(game)
        # The normal trigger may already start the approach on this frame.
        if not game.social.active:
            self.assertTrue(quest.begin_encounter(game.combat.start_mill))
        self.assertEqual(game.social.script_identifier, 'mill_encounter_intro')
        return quest

    def reach_cue(self, game):
        for _ in range(100):
            page = game.social.page
            if page.get('cue') == 'mill_battle_music':
                self.frame(game)
                return page
            self.assertEqual(game.music.desired_track, 'eldenmere')
            key(game, pygame.K_SPACE)
            self.frame(game)
        self.fail('The approach did not present Mira\'s authored music cue')

    def begin_bat(self, game):
        if game.quests.status(MILL_QUEST) != 'completed':seed_completed_mill(game)
        game.world = game.town
        game.player.position.update(game.combat.position+(0, 24))
        game.opening_fade = game.transfer_cooldown = 0
        self.frame(game)
        self.assertTrue(game.combat.interact())
        return game.combat.scene

    def test_title_to_new_game_keeps_the_same_eldenmere_stream(self):
        game = self.game(title=True)
        game.title.start_music()
        self.frame(game)
        self.assertEqual(game.music.desired_track, 'eldenmere')
        loads, starts = self.backend.load.call_count, self.backend.play.call_count
        self.assertEqual(loads, 1)
        game.title.activate()  # New Game uses the title's actual fade path.
        self.frame(game, 1)
        self.assertFalse(game.on_title)
        self.assertEqual(game.music.desired_track, 'eldenmere')
        self.assertEqual(self.backend.load.call_count, loads)
        self.assertEqual(self.backend.play.call_count, starts)

    def test_town_interior_and_millrace_share_the_exploration_stream(self):
        game = self.game()
        seed_completed_mill(game)
        self.frame(game)
        starts = self.backend.play.call_count
        for identifier in ('sanctuary_hall', 'upstream', 'eldenmere'):
            if identifier == 'eldenmere':world = game.town
            else:world = game._scene_by_id(identifier)
            game.world = world
            game.player.position.update(world.data['spawn'])
            self.frame(game)
            self.assertEqual(game.music.desired_track, 'eldenmere')
        self.assertEqual(self.backend.play.call_count, starts)

    def test_bat_transition_freezes_gameplay_then_flee_restores_exploration_music(self):
        game = self.game();scene = self.begin_bat(game)
        self.assertTrue(game.combat.transitioning)
        self.assertEqual(game.music.desired_track, 'battle')
        before = game.elapsed_ms, game.player.position.copy()
        key(game, pygame.K_SPACE)
        self.frame(game, .05)
        self.assertEqual([a.atb for a in (*scene.model.party, scene.model.enemy)], [0, 0])
        self.assertEqual((game.elapsed_ms, game.player.position), before)
        self.finish_transition(game)
        for _ in range(200):
            if scene.model.waiting_for_player:break
            self.frame(game, .1)
        self.assertTrue(scene.model.waiting_for_player)
        game.draw();click(game, scene.command_rects['flee'].center)
        for _ in range(50):
            if scene.model.ended:break
            self.frame(game, .1)
        self.assertEqual(scene.model.phase, 'fled')
        game.draw();click(game, scene.continue_rect.center)
        self.assertFalse(game.combat.active)
        self.assertEqual(game.music.desired_track, 'eldenmere')

    def test_mill_music_starts_when_miras_back_away_line_is_presented(self):
        game = self.game();self.seed_encounter(game)
        page = self.reach_cue(game)
        self.assertIn('Back slowly', ' '.join(page['lines']))
        self.assertEqual(game.music.desired_track, 'battle')
        self.assertFalse(game.combat.active)
        # Allow the nonblocking music fade to finish while the player reads.
        self.frame(game, .6)
        battle_loads = self.backend.load.call_count
        read_social(game)
        self.assertTrue(game.combat.active)
        self.assertTrue(game.combat.transitioning)
        self.finish_transition(game)
        self.assertEqual(game.music.desired_track, 'battle')
        self.assertEqual(self.backend.load.call_count, battle_loads)

    def test_canceling_before_the_cue_keeps_exploration_music(self):
        game = self.game();quest = self.seed_encounter(game)
        self.assertEqual(game.music.desired_track, 'eldenmere')
        self.assertTrue(game.social.cancel())
        self.assertEqual(game.music.desired_track, 'eldenmere')
        self.assertTrue(quest.encounter_pending)
        self.assertFalse(game.combat.active)

    def test_mill_victory_and_reward_retry_keep_fanfare_until_spoils_exit(self):
        game = self.game();self.seed_encounter(game);self.reach_cue(game)
        read_social(game)
        scene = finish_mill_battle(game, dismiss=False)
        self.assertEqual(scene.model.phase, 'victory')
        self.assertEqual(game.music.desired_track, 'victory')
        with patch.object(game.lattice_progression, 'award_battle_rewards', return_value=False):
            spoils = wait_for_spoils(game)
        self.assertTrue(game.combat.active)
        self.assertTrue(spoils.result_error)
        self.assertEqual(game.music.desired_track, 'victory')
        acknowledge_battle_result(game, scene)
        self.assertFalse(game.combat.active)
        self.assertTrue(game.mill_quest.encounter_cleared)
        self.assertEqual(game.music.desired_track, 'eldenmere')
        self.assertEqual(game.social.script_identifier, 'mill_aftermath')

    def test_miras_tutorial_ducks_music_without_pausing_or_restarting_it(self):
        game = self.game();self.seed_encounter(game);self.reach_cue(game)
        read_social(game);self.finish_transition(game)
        scene = game.combat.scene
        for _ in range(200):
            if scene.tutorial_active:break
            self.frame(game, .1)
        self.assertTrue(scene.tutorial_active)
        self.backend.pause.reset_mock()
        starts = self.backend.play.call_count
        self.frame(game, .5)
        ducked_volume = self.backend.set_volume.call_args.args[0]
        self.assertGreater(ducked_volume, 0)
        self.assertFalse(game.music.paused)
        self.backend.pause.assert_not_called()
        while scene.tutorial_active:key(game, pygame.K_SPACE)
        self.frame(game, .5)
        self.assertGreater(self.backend.set_volume.call_args.args[0], ducked_volume)
        self.assertEqual(self.backend.play.call_count, starts)

    def test_walking_away_after_the_cue_restores_music_and_retry_replays_the_cue(self):
        game = self.game();quest = self.seed_encounter(game)
        self.reach_cue(game)
        self.assertEqual(game.music.desired_track, 'battle')
        game.player.position.update(180, 510)
        self.frame(game)
        self.assertFalse(game.social.active)
        self.assertEqual(game.music.desired_track, 'eldenmere')
        self.assertTrue(quest.encounter_pending)
        self.assertFalse(game.combat.active)
        game.player.position.update(180, 374)
        quest._place_mira(quest.upstream, (156, 374))
        self.assertTrue(quest.begin_encounter(game.combat.start_mill))
        self.frame(game)
        self.assertEqual(game.music.desired_track, 'eldenmere')
        self.reach_cue(game)
        self.assertEqual(game.music.desired_track, 'battle')

    def test_quit_during_the_music_cue_restores_a_fresh_exploration_score(self):
        game = self.game();self.seed_encounter(game);self.reach_cue(game)
        self.assertEqual(game.music.desired_track, 'battle')
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        self.assertFalse(game.handle_events())
        saved = json.loads(self.path.read_text())
        self.assertNotIn('music', saved)
        self.assertNotIn('mill_battle_music', json.dumps(saved))
        restored = self.game(title=True)
        self.assertTrue(restored.has_saved_journey)
        self.assertTrue(restored.begin_journey(True))
        self.assertEqual(restored.music.desired_track, 'eldenmere')
        self.assertTrue(restored.mill_quest.encounter_pending)
        self.assertFalse(restored.combat.active)

    def test_ready_atb_keeps_music_running_and_focus_pause_preserves_its_position(self):
        game = self.game();scene = self.begin_bat(game)
        self.finish_transition(game)
        for _ in range(200):
            if scene.model.waiting_for_player:break
            self.frame(game, .1)
        gauges = scene.model.player.atb, scene.model.enemy.atb
        self.assertTrue(scene.model.waiting_for_player)
        self.backend.pause.reset_mock();self.backend.unpause.reset_mock()
        starts = self.backend.play.call_count
        self.frame(game, 4)
        self.assertEqual((scene.model.player.atb, scene.model.enemy.atb), gauges)
        self.backend.pause.assert_not_called()
        pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertTrue(game.handle_events());self.frame(game)
        self.backend.pause.assert_called_once()
        pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        self.assertTrue(game.handle_events());self.frame(game)
        self.backend.unpause.assert_not_called()
        key(game, pygame.K_ESCAPE);self.frame(game)
        self.backend.unpause.assert_called_once()
        self.assertEqual(self.backend.play.call_count, starts)

    def test_music_volume_changes_live_and_effects_remain_independent(self):
        game = self.game();seed_completed_mill(game);self.frame(game, 1)
        game.audio.set_music(.6)
        gain = game.music.tracks['eldenmere']['gain']
        self.assertAlmostEqual(self.backend.set_volume.call_args.args[0], gain*.6)
        calls = self.backend.set_volume.call_count
        game.audio.set_effects(.3)
        self.assertEqual(self.backend.set_volume.call_count, calls)
        game.audio.set_music(0)
        self.assertEqual(self.backend.set_volume.call_args.args[0], 0)
        self.begin_bat(game)
        self.finish_transition(game)
        game.audio.set_music(.7)
        self.frame(game, .5)
        self.assertEqual(game.music.desired_track, 'battle')
        self.assertGreater(self.backend.set_volume.call_args.args[0], 0)


if __name__ == '__main__':unittest.main()
