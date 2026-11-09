"""Victory presentation, resumed soundtrack and durable real-game spoils."""
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
from inventory import MAX_QUANTITY
from main import Game
import test_battle_gameplay as bat_fixture
import test_mill_battle_gameplay as mill_fixture
from test_mill_battle_gameplay import (
    acknowledge_battle_result, click, key, seed_completed_mill, wait_for_spoils,
)
from ui_style import Painter


class SpoilsGameplayTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='spoils-gameplay-')
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.path = self.directory/'journey.json'
        self.backend = MagicMock()
        self.backend.get_busy.return_value = True
        self.backend.get_pos.return_value = 0
        stream = patch('pygame.mixer.music', self.backend)
        stream.start();self.addCleanup(stream.stop)

    def tearDown(self):pygame.quit()

    def game(self, *, title=False):
        game = Game(window_size=(960, 640), fullscreen=False, start_on_title=title,
                    save_path=self.path, settings_path=self.directory/'settings.json')
        game.audio.set_music(1);game.audio.set_effects(0)
        pygame.event.clear()
        if not title:seed_completed_mill(game)
        return game

    def bat(self, game):
        game.world = game.town
        game.player.position.update(game.combat.position+(0, 24))
        game.player.facing = 'back'
        game.opening_fade = game.transfer_cooldown = 0
        game.camera.reset()
        self.assertTrue(game.combat.interact())
        return game.combat.scene

    def win(self, game, scene):
        # The fixture's ordinary input driver attacks the actual Bat.
        driver = bat_fixture.BattleGameplayTests()
        driver.finish(game, scene)
        self.assertEqual(scene.model.phase, 'victory')
        self.assertEqual(game.combat.post_phase, 'banner')
        return scene

    def state(self, game):
        return (game.attributes.to_dict(), game.battle_rewards.to_dict(), game.inventory.to_dict(),
                game.quests.to_dict(), game.mill_quest.to_dict(), game.character_progression.to_dict())

    def finish_presentation(self, game, spoils):
        for _ in range(20):
            if spoils.presentation_complete:return
            key(game, pygame.K_RETURN)
            game.update(0, (0, 0), False)
        self.fail('EXP and level-up presentation did not finish')

    def continue_spoils(self, game, spoils):
        self.finish_presentation(game, spoils)
        game.draw();click(game, spoils.continue_rect.center)

    def quit(self, game):
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        self.assertFalse(game.handle_events())

    def load(self):
        game = self.game(title=True)
        self.assertTrue(game.has_saved_journey)
        self.assertTrue(game.begin_journey(True))
        pygame.event.clear()
        return game

    def test_victory_resumes_world_score_and_banner_without_awarding_or_accepting_continue(self):
        game = self.game();scene = self.bat(game);before = self.state(game)
        self.win(game, scene)
        self.assertEqual(game.music.desired_track, 'eldenmere')
        self.backend.play.assert_called_with(-1)
        self.assertEqual(self.state(game), before)
        with patch.object(Painter, 'text', autospec=True, wraps=Painter.text) as texts:
            game.draw()
        labels = ' '.join(str(call.args[1]) for call in texts.call_args_list)
        self.assertIn('VICTORY', labels)
        for label in ('Continue', 'Resonance Points', 'Emerald'):
            self.assertNotIn(label, labels)
        key(game, pygame.K_RETURN);key(game, pygame.K_SPACE)
        click(game, scene.continue_rect.center)
        game.update(.05, (1, 0), True)
        self.assertTrue(game.combat.active)
        self.assertEqual(game.combat.post_phase, 'banner')
        self.assertEqual(self.state(game), before)

    def test_spoils_awards_before_continue_and_holds_world_without_duplicate_rewards(self):
        game = self.game();scene = self.bat(game);self.win(game, scene)
        frozen = game.elapsed_ms, game.player.position.copy()
        spoils = wait_for_spoils(game)
        self.assertTrue(spoils.awarded)
        self.assertTrue(game.combat.active)
        self.assertEqual(len(game.battle_rewards.to_dict()['receipts']), 1)
        self.assertEqual(game.inventory.quantity('aether_emerald'), 1)
        self.assertEqual(game.attributes.current_hp, scene.model.player.hp)
        committed = self.state(game)
        for _ in range(20):game.update(.5, (1, 0), True)
        self.assertEqual(self.state(game), committed)
        self.assertEqual((game.elapsed_ms, game.player.position), frozen)
        self.continue_spoils(game, spoils)
        self.assertFalse(game.combat.active)
        self.assertEqual(game.music.desired_track, 'eldenmere')
        self.assertEqual(self.state(game), committed)
        self.assertIsNone(json.loads(self.path.read_text()).get('post_battle'))

    def test_resumed_world_score_keeps_playing_through_volume_focus_and_waiting(self):
        game = self.game();scene = self.bat(game);self.win(game, scene)
        spoils = wait_for_spoils(game)
        game.update(.1, (0, 0), False)
        self.assertFalse(game.music.completed)
        self.assertTrue(game.music.playing)
        starts, loads = self.backend.play.call_count, self.backend.load.call_count
        for _ in range(20):game.update(.5, (0, 0), False)
        game.audio.set_music(0);game.audio.set_music(.7)
        pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertTrue(game.handle_events());game.update(.1, (0, 0), False)
        pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        self.assertTrue(game.handle_events());key(game, pygame.K_ESCAPE)
        game.update(.1, (0, 0), False)
        self.assertEqual(game.music.desired_track, 'eldenmere')
        self.assertEqual(self.backend.play.call_count, starts)
        self.assertEqual(self.backend.load.call_count, loads)
        self.assertTrue(game.music.playing)
        self.assertTrue(spoils.awarded)
        self.continue_spoils(game, spoils)
        self.assertEqual(game.music.desired_track, 'eldenmere')

    def test_quit_during_victory_banner_resumes_world_score_and_awards_once(self):
        game = self.game();scene = self.bat(game);self.win(game, scene)
        self.assertEqual(len(game.battle_rewards.to_dict()['receipts']), 0)
        self.quit(game)
        saved = json.loads(self.path.read_text())
        self.assertIsNotNone(saved.get('post_battle'))
        restored = self.load();spoils = wait_for_spoils(restored)
        self.assertTrue(spoils.awarded)
        self.assertEqual(restored.music.desired_track, 'eldenmere')
        self.assertEqual(restored.music.desired_track, 'eldenmere')
        self.assertEqual(len(restored.battle_rewards.to_dict()['receipts']), 1)
        self.assertEqual(restored.inventory.quantity('aether_emerald'), 1)
        committed = self.state(restored)
        for _ in range(5):restored.update(1, (0, 0), False)
        self.assertEqual(self.state(restored), committed)
        self.continue_spoils(restored, spoils)
        self.assertFalse(restored.combat.active)
        self.assertEqual(self.state(restored), committed)

    def test_quit_during_spoils_transition_preserves_victory_for_resume(self):
        game = self.game();scene = self.bat(game);self.win(game, scene)
        for _ in range(100):
            if game.combat.post_phase == 'spoils_transition':break
            game.update(.02, (0, 0), False)
        self.assertEqual(game.combat.post_phase, 'spoils_transition')
        self.quit(game)
        restored = self.load();wait_for_spoils(restored)
        self.assertEqual(len(restored.battle_rewards.to_dict()['receipts']), 1)
        self.assertEqual(restored.inventory.quantity('aether_emerald'), 1)
        self.assertEqual(restored.music.desired_track, 'eldenmere')

    def test_quit_on_awarded_spoils_retains_receipt_and_never_awards_again(self):
        game = self.game();scene = self.bat(game);self.win(game, scene)
        wait_for_spoils(game);committed = self.state(game)
        self.quit(game)
        restored = self.load();spoils = wait_for_spoils(restored)
        self.assertTrue(spoils.awarded)
        self.assertEqual(self.state(restored), committed)
        self.assertEqual(restored.music.desired_track, 'eldenmere')
        self.continue_spoils(restored, spoils)
        self.assertEqual(self.state(restored), committed)
        again = self.load()
        self.assertFalse(again.combat.active)
        self.assertEqual(self.state(again), committed)

    def test_reward_refusal_uses_spoils_retry_and_does_not_allow_early_exit(self):
        game = self.game();scene = self.bat(game);self.win(game, scene)
        before = self.state(game)
        with patch.object(game.battle_rewards, 'award_battle_rewards', return_value=False):
            spoils = wait_for_spoils(game)
            self.assertFalse(spoils.awarded)
            self.assertTrue(spoils.result_error)
            self.assertEqual(self.state(game), before)
            key(game, pygame.K_RETURN)
            self.assertTrue(game.combat.active)
            self.assertEqual(self.state(game), before)
        game.draw();click(game, spoils.retry_rect.center);game.update(0, (0, 0), False)
        self.assertTrue(spoils.awarded)
        self.assertEqual(len(game.battle_rewards.to_dict()['receipts']), 1)
        self.assertEqual(game.inventory.quantity('aether_emerald'), 1)
        self.continue_spoils(game, spoils)
        self.assertFalse(game.combat.active)
        self.assertEqual(len(game.battle_rewards.to_dict()['receipts']), 1)

    def test_failed_victory_checkpoint_blocks_awards_until_retry_can_save(self):
        game = self.game();scene = self.bat(game)
        self.assertTrue(game.save_progress())
        with patch('save_game.os.replace', side_effect=OSError('disk unavailable')):
            self.win(game, scene)
            spoils = wait_for_spoils(game)
            self.assertFalse(spoils.awarded)
            self.assertTrue(spoils.result_error)
            self.assertEqual(len(game.battle_rewards.to_dict()['receipts']), 0)
            self.assertEqual(game.inventory.quantity('aether_emerald'), 0)
            self.assertIsNone(json.loads(self.path.read_text()).get('post_battle'))
        game.draw();click(game, spoils.retry_rect.center)
        self.assertTrue(spoils.awarded)
        self.assertEqual(len(game.battle_rewards.to_dict()['receipts']), 1)
        self.assertEqual(game.inventory.quantity('aether_emerald'), 1)
        self.assertEqual(json.loads(self.path.read_text())['post_battle']['stage'], 'awarded')

    def test_failed_award_checkpoint_retries_the_save_without_awarding_twice(self):
        game = self.game();scene = self.bat(game);self.win(game, scene)
        self.assertEqual(json.loads(self.path.read_text())['post_battle']['stage'], 'pending')
        with patch('save_game.os.replace', side_effect=OSError('disk unavailable')):
            spoils = wait_for_spoils(game)
            self.assertFalse(spoils.awarded)
            self.assertTrue(spoils.result_error)
            self.assertEqual(len(game.battle_rewards.to_dict()['receipts']), 1)
            self.assertEqual(game.inventory.quantity('aether_emerald'), 1)
            self.assertEqual(game.combat.snapshot()['stage'], 'awarded')
            self.assertEqual(json.loads(self.path.read_text())['post_battle']['stage'], 'pending')
            key(game, pygame.K_RETURN)
            self.assertEqual(len(game.battle_rewards.to_dict()['receipts']), 1)
        game.draw();click(game, spoils.retry_rect.center)
        self.assertTrue(spoils.awarded)
        self.assertFalse(spoils.result_error)
        self.assertEqual(len(game.battle_rewards.to_dict()['receipts']), 1)
        self.assertEqual(game.inventory.quantity('aether_emerald'), 1)
        self.quit(game);restored = self.load();wait_for_spoils(restored)
        self.assertEqual(len(restored.battle_rewards.to_dict()['receipts']), 1)
        self.assertEqual(restored.inventory.quantity('aether_emerald'), 1)

    def test_failed_exit_checkpoint_keeps_spoils_and_music_until_explicit_retry(self):
        game = self.game();scene = self.bat(game);self.win(game, scene)
        spoils = wait_for_spoils(game);committed = self.state(game)
        with patch('save_game.os.replace', side_effect=OSError('disk unavailable')):
            self.continue_spoils(game, spoils)
            self.assertTrue(game.combat.active)
            self.assertTrue(spoils.result_error)
            self.assertEqual(game.music.desired_track, 'eldenmere')
            self.assertEqual(self.state(game), committed)
        game.draw();click(game, spoils.retry_rect.center)
        self.assertTrue(spoils.awarded)
        self.continue_spoils(game, spoils)
        self.assertFalse(game.combat.active)
        self.assertEqual(game.music.desired_track, 'eldenmere')
        self.assertEqual(self.state(game), committed)
        self.assertIsNone(json.loads(self.path.read_text()).get('post_battle'))

    def test_mill_incapacitation_recovers_on_spoils_and_reload_waits_for_aftermath_exit(self):
        game = Game(window_size=(960, 640), fullscreen=False, start_on_title=False,
                    save_path=self.path, settings_path=self.directory/'settings.json')
        game.audio.set_music(1);game.audio.set_effects(0);pygame.event.clear()
        driver = mill_fixture.MillBattleGameplayTests()
        driver.directory, driver.path, driver.game = self.directory, self.path, game
        scene = driver.start()
        scene.model.player.hp = 0
        # Seed the final knockout/victory boundary. Ordinary tutorial combat
        # is covered separately; this checks first aid, EXP eligibility and
        # the durable aftermath rather than requiring Mira to solo the boss.
        scene.model.enemy.hp = 0
        scene.model._result('victory')
        game.combat.transition = None
        game.update(0, (0, 0), False)
        self.assertGreater(scene.model.combatant('mira').hp, 0)
        spoils = wait_for_spoils(game)
        self.assertTrue(spoils.awarded)
        self.assertEqual(game.attributes.current_hp, game.attributes.value('hp')//4)
        self.assertEqual(len(game.battle_rewards.to_dict()['receipts']), 1)
        self.assertTrue(game.mill_quest.encounter_cleared)
        self.assertFalse(game.mill_quest.aftermath_done)
        self.assertFalse(game.social.active)
        self.quit(game)
        restored = self.load();spoils = wait_for_spoils(restored)
        self.assertEqual(restored.music.desired_track, 'eldenmere')
        self.assertEqual(len(restored.battle_rewards.to_dict()['receipts']), 1)
        self.assertEqual(restored.attributes.current_hp, restored.attributes.value('hp')//4)
        self.assertFalse(restored.social.active)
        game = restored
        self.continue_spoils(game, spoils)
        self.assertFalse(game.combat.active)
        self.assertEqual(game.social.script_identifier, 'mill_aftermath')
        self.assertTrue(any('bandage' in ' '.join(page['lines']).lower() for page in game.social.pages))
        self.assertTrue(game.world.can_stand(game.player.position))
        mill_fixture.read_social(game)
        self.assertTrue(game.mill_quest.aftermath_done)
        self.assertEqual(len(game.battle_rewards.to_dict()['receipts']), 1)

    def test_reward_storage_caps_display_and_award_only_available_room(self):
        game = self.game()
        self.assertTrue(game.award_battle_rewards('fixture:almost-full',
                                                 {'aether_emerald': MAX_QUANTITY}))
        scene = self.bat(game);self.win(game, scene);spoils = wait_for_spoils(game)
        self.assertEqual(scene.model.enemy_definition['rewards'], {'drops': {}})
        self.assertEqual(len(game.battle_rewards.to_dict()['receipts']), 2)
        self.assertEqual(game.inventory.quantity('aether_emerald'), MAX_QUANTITY)
        self.assertTrue(spoils.awarded)
        acknowledge_battle_result(game, scene)
        self.assertEqual(len(game.battle_rewards.to_dict()['receipts']), 2)

    def test_entry_inputs_held_through_spoils_reveal_cannot_collect_and_exit_in_one_press(self):
        game = self.game();scene = self.bat(game);self.win(game, scene)
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, repeat=False))
        self.assertTrue(game.handle_events())
        spoils = wait_for_spoils(game)
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, repeat=True))
        self.assertTrue(game.handle_events())
        self.assertTrue(game.combat.active)
        self.assertFalse(spoils.dismissed)
        pygame.event.post(pygame.event.Event(pygame.KEYUP, key=pygame.K_RETURN))
        self.assertTrue(game.handle_events())
        key(game, pygame.K_RETURN)
        self.assertTrue(game.combat.active)  # First fresh press finishes EXP.
        self.assertTrue(spoils.presentation_complete)
        key(game, pygame.K_RETURN)
        self.assertFalse(game.combat.active)

    def test_spoils_focus_pause_resize_and_large_text_keep_the_exit_readable(self):
        game = self.game();scene = self.bat(game);self.win(game, scene)
        spoils = wait_for_spoils(game)
        pygame.event.post(pygame.event.Event(pygame.VIDEORESIZE, w=480, h=320))
        self.assertTrue(game.handle_events());game.audio.set_text_scale(1.5);game.draw()
        self.assertTrue(pygame.Rect(0, 0, 480, 320).contains(spoils.continue_rect))
        self.assertEqual(game.ui_surface.get_clip(), game.ui_surface.get_rect())
        pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertTrue(game.handle_events());self.assertTrue(spoils.paused)
        click(game, spoils.continue_rect.center)
        self.assertTrue(game.combat.active)
        pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        self.assertTrue(game.handle_events());self.assertTrue(spoils.paused)
        key(game, pygame.K_ESCAPE)
        self.assertFalse(spoils.paused)
        self.continue_spoils(game, spoils)
        self.assertFalse(game.combat.active)


if __name__ == '__main__':unittest.main()
