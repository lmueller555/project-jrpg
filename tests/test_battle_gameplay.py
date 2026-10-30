"""Real Eldenmere encounter input, wait-ATB isolation and durable settlement."""
import json
import os
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
from aether_lattice import MAX_RP
from inventory import MAX_QUANTITY
from main import Game
from test_mill_battle_gameplay import acknowledge_battle_result, seed_completed_mill, wait_for_spoils


class BattleGameplayTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='battle-gameplay-test-')
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.path = self.directory/'journey.json'

    def tearDown(self):pygame.quit()

    def game(self, title=False):
        game = Game(window_size=(960, 640), fullscreen=False,
                    start_on_title=title, save_path=self.path,
                    settings_path=self.directory/'settings.json')
        game.audio.set_music(0);game.audio.set_effects(0)
        pygame.event.clear()
        if not title:seed_completed_mill(game)
        return game

    def key(self, game, key):
        for kind in (pygame.KEYDOWN, pygame.KEYUP):
            pygame.event.post(pygame.event.Event(kind, key=key, repeat=False))
        self.assertTrue(game.handle_events())

    def point(self, game, logical):
        width, height = game.window.get_size()
        scale = max(1, min(width//480, height//320))
        return (round((width-480*scale)//2+logical[0]*scale),
                round((height-320*scale)//2+logical[1]*scale))

    def click(self, game, logical):
        point = self.point(game, logical)
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            pygame.event.post(pygame.event.Event(kind, button=1, pos=point))
        self.assertTrue(game.handle_events())

    def snapshot(self, game):
        return (game.attributes.to_dict(), game.lattice.to_dict(),
                game.inventory.to_dict(), game.quests.to_dict(),
                sorted(game.social.flags))

    def place_by_bat(self, game):
        game.world = game.town
        game.player.position.update(game.combat.position+(0, 24))
        self.assertTrue(game.world.can_stand(game.player.position))
        game.player.facing = 'back'
        game.camera.reset()

    def start(self, game):
        self.place_by_bat(game)
        self.key(game, pygame.K_e)
        self.assertTrue(game.combat.active)
        scene = game.combat.scene
        scene.model.rng = random.Random(7)
        self.assertEqual(scene.model.enemy_id, 'bat')
        self.assertEqual(scene.model.player.hp, game.attributes.current_hp)
        game.draw()
        return scene

    def advance_until(self, game, predicate, limit=2000):
        for _ in range(limit):
            if predicate():return
            game.update(.1, (1, 0), True)
        self.fail('Battle did not reach the expected state.')

    def ready(self, game, scene):
        self.advance_until(game, lambda: scene.model.waiting_for_player)
        game.draw()

    def action(self, game, scene, identifier):
        self.ready(game, scene)
        self.assertIn(identifier, scene.command_rects)
        self.click(game, scene.command_rects[identifier].center)
        self.assertEqual(scene.model.phase, 'acting')
        self.assertEqual(scene.model.current_action.action, identifier)

    def finish(self, game, scene, command='attack'):
        for _ in range(3000):
            if scene.model.ended:return
            if scene.model.waiting_for_player:
                game.draw()
                self.click(game, scene.command_rects[command].center)
            else:game.update(.1, (1, 0), True)
        self.fail('The battle did not finish.')

    def dismiss(self, game, scene):
        self.assertTrue(scene.model.ended)
        acknowledge_battle_result(game, scene)
        self.assertFalse(game.combat.active)

    def test_bat_is_reachable_and_approaching_starts_battle_without_an_action_key(self):
        game = self.game()
        self.assertFalse(game.combat.active)
        self.assertTrue(game.world.can_stand(game.combat.position))
        self.assertFalse(game.combat.interact())
        self.place_by_bat(game)
        game.update(.1, (0, 0), False)
        self.assertTrue(game.combat.active)
        self.assertEqual(game.combat.scene.model.enemy.name, 'Bat')

    def test_opening_and_menus_block_an_encounter_without_consuming_resources(self):
        game = self.game()
        self.place_by_bat(game)
        before = self.snapshot(game)
        game.opening.stage = 'wake';game.opening._sleeping = True
        self.assertTrue(game.opening.locks_player)
        self.assertFalse(game.combat.interact())
        game.opening.stage = 'disabled';game.opening._sleeping = False
        game.pause.open()
        self.assertFalse(game.combat.interact())
        self.key(game, pygame.K_e)
        self.assertFalse(game.combat.active)
        game.pause.close()
        game.inventory_ui.open()
        self.assertFalse(game.combat.interact())
        game.inventory_ui.close()
        self.assertEqual(self.snapshot(game), before)
        self.assertTrue(game.combat.interact())

    def test_world_and_all_gauges_pause_while_player_decides(self):
        game = self.game()
        scene = self.start(game)
        self.ready(game, scene)
        gauges = scene.model.player.atb, scene.model.enemy.atb
        self.assertEqual(gauges[0], 1)
        self.assertGreater(gauges[1], 0)
        self.assertNotIn('aether_dart', scene.command_rects)
        before = self.snapshot(game)
        elapsed = game.elapsed_ms
        player = game.player.position.copy()
        npcs = [actor.position.copy() for actor in game.persistent_npcs]
        for _ in range(100):game.update(.25, (1, 0), True)
        self.assertEqual((scene.model.player.atb, scene.model.enemy.atb), gauges)
        self.assertEqual(scene.model.phase, 'ready')
        self.assertEqual(game.elapsed_ms, elapsed)
        self.assertEqual(game.player.position, player)
        self.assertEqual([actor.position for actor in game.persistent_npcs], npcs)
        self.assertEqual(self.snapshot(game), before)
        for key in (pygame.K_i, pygame.K_j, pygame.K_m):self.key(game, key)
        self.assertFalse(game.inventory_ui.is_open)
        self.assertFalse(game.quest_ui.journal_open)
        self.assertFalse(game.map_open)

    def test_victory_awards_on_spoils_and_continue_returns_with_real_rewards(self):
        game = self.game()
        scene = self.start(game)
        before = self.snapshot(game)
        self.assertTrue(game.save_progress())
        self.finish(game, scene)
        self.assertEqual(scene.model.phase, 'victory')
        self.assertLess(scene.model.player.hp, game.attributes.current_hp)
        self.assertEqual(self.snapshot(game), before)  # Rewards wait for the separate Spoils screen.
        final_hp, final_mp = scene.model.player.hp, scene.model.player.mp
        self.dismiss(game, scene)
        self.assertEqual((game.attributes.current_hp, game.attributes.current_mp), (final_hp, final_mp))
        self.assertEqual(game.lattice.state()['rp'], 20)
        self.assertEqual(game.lattice.rank(), 2)
        self.assertEqual(game.lattice.steps(), 1)
        self.assertEqual(game.inventory.quantity('aether_emerald'), 1)
        self.assertEqual(game.quests.to_dict(), before[3])
        self.assertEqual(sorted(game.social.flags), before[4])
        committed = self.snapshot(game)
        saved = json.loads(self.path.read_text())
        self.assertEqual(saved['character_attributes'], game.attributes.to_dict())
        self.assertEqual(saved['aether_lattice'], game.lattice.to_dict())
        self.assertEqual(saved['inventory'], game.inventory.to_dict())
        game.combat.update(0);game.combat.update(0)
        self.assertEqual(self.snapshot(game), committed)
        restored = self.game(title=True)
        self.assertTrue(restored.has_saved_journey)
        self.assertTrue(restored.begin_journey(True))
        self.assertFalse(restored.combat.active)
        self.assertEqual(self.snapshot(restored), committed)

    def test_guard_then_flee_commits_damage_without_reward_or_rank_gain(self):
        game = self.game()
        self.assertTrue(game.attributes.set_current(hp=100, mp=17))
        scene = self.start(game)
        before_lattice = game.lattice.to_dict()
        before_inventory = game.inventory.to_dict()
        self.action(game, scene, 'guard')
        self.advance_until(game, lambda: scene.model.player.hp < 100)
        self.assertEqual(game.attributes.current_hp, 100)
        self.action(game, scene, 'flee')
        self.advance_until(game, lambda: scene.model.ended)
        self.assertEqual(scene.model.phase, 'fled')
        expected = scene.model.player.hp, scene.model.player.mp
        self.dismiss(game, scene)
        self.assertEqual((game.attributes.current_hp, game.attributes.current_mp), expected)
        self.assertLess(expected[0], 100)
        self.assertEqual(game.lattice.to_dict(), before_lattice)
        self.assertEqual(game.inventory.to_dict(), before_inventory)

    def test_technical_reward_limits_show_zero_rewards_and_still_allow_victory_return(self):
        game = self.game()
        self.assertTrue(game.award_battle_rewards('test:full-reward-storage',
                                                 {'caelan': MAX_RP},
                                                 {'aether_emerald': MAX_QUANTITY}))
        scene = self.start(game)
        receipt = game.combat.receipt_id
        before_lattice, before_inventory = game.lattice.to_dict(), game.inventory.to_dict()
        self.assertEqual(scene.model.enemy_definition['rewards'], {'rp': 0, 'drops': {}})
        self.finish(game, scene)
        self.assertEqual(scene.model.phase, 'victory')
        expected = scene.model.player.hp, scene.model.player.mp
        self.dismiss(game, scene)
        self.assertEqual((game.attributes.current_hp, game.attributes.current_mp), expected)
        after_lattice = game.lattice.to_dict()
        self.assertEqual(after_lattice['characters'], before_lattice['characters'])
        self.assertEqual(after_lattice['receipts'], sorted(before_lattice['receipts']+[receipt]))
        self.assertEqual(game.inventory.to_dict(), before_inventory)
        self.assertTrue(game.lattice.has_receipt(receipt))
        self.assertFalse(scene.result_error)
        self.assertIsNone(game.save_error)

    def test_lattice_learned_magick_uses_battle_mp_and_settles_it_on_return(self):
        game = self.game()
        self.assertTrue(game.award_battle_rewards('test:unlock-dart', {'caelan': 10000},
                                                 {'aether_diamond': 1}))
        self.assertTrue(game.move_lattice('aether_dart_01'))
        self.assertTrue(game.activate_lattice('aether_dart_01'))
        scene = self.start(game)
        initial_mp = game.attributes.current_mp
        self.action(game, scene, 'aether_dart')
        self.assertEqual(scene.model.player.mp, initial_mp-4)
        self.assertEqual(game.attributes.current_mp, initial_mp)
        self.finish(game, scene)
        self.assertEqual(scene.model.phase, 'victory')
        self.dismiss(game, scene)
        self.assertEqual(game.attributes.current_mp, initial_mp-4)
        self.assertEqual(game.lattice.state()['rp'], 10020)
        self.assertEqual(game.inventory.quantity('aether_diamond'), 0)

    def test_reward_rejection_keeps_result_open_and_all_persistent_state_unchanged(self):
        game = self.game()
        scene = self.start(game)
        self.finish(game, scene)
        self.assertEqual(scene.model.phase, 'victory')
        before = self.snapshot(game)
        with patch.object(game.lattice_progression, 'award_battle_rewards', return_value=False):
            spoils = wait_for_spoils(game)
        self.assertTrue(game.combat.active)
        self.assertIs(game.combat.scene, scene)
        self.assertFalse(scene.dismissed)
        self.assertTrue(spoils.result_error)
        self.assertEqual(self.snapshot(game), before)
        self.dismiss(game, scene)
        self.assertEqual(game.lattice.state()['rp'], 20)
        self.assertEqual(game.inventory.quantity('aether_emerald'), 1)
        self.assertEqual(game.attributes.current_hp, scene.model.player.hp)

    def test_defeat_restores_prebattle_resources_without_quest_rewind_or_rewards(self):
        game = self.game()
        self.assertTrue(game.attributes.set_current(hp=1, mp=5))
        scene = self.start(game)
        before = self.snapshot(game)
        self.finish(game, scene)
        self.assertEqual(scene.model.phase, 'defeat')
        self.assertEqual(scene.model.player.hp, 0)
        self.dismiss(game, scene)
        self.assertEqual(self.snapshot(game), before)
        self.assertEqual((game.attributes.current_hp, game.attributes.current_mp), (1, 5))

    def test_quit_mid_battle_checkpoints_only_the_prebattle_persistent_state(self):
        game = self.game()
        self.assertTrue(game.attributes.set_current(hp=100, mp=17))
        scene = self.start(game)
        before = self.snapshot(game)
        self.action(game, scene, 'guard')
        self.advance_until(game, lambda: scene.model.player.hp < 100)
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        self.assertFalse(game.handle_events())
        self.assertEqual(self.snapshot(game), before)
        saved = json.loads(self.path.read_text())
        self.assertEqual(saved['character_attributes'], before[0])
        self.assertEqual(saved['aether_lattice'], before[1])
        self.assertEqual(saved['inventory'], before[2])
        restored = self.game(title=True)
        self.assertTrue(restored.begin_journey(True))
        self.assertFalse(restored.combat.active)
        self.assertEqual(self.snapshot(restored), before)

    def test_focus_loss_and_escape_pause_battle_without_opening_exploration_menu(self):
        game = self.game()
        scene = self.start(game)
        game.update(1, (0, 0), False)
        pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertTrue(game.handle_events())
        self.assertTrue(scene.paused)
        gauges = scene.model.player.atb, scene.model.enemy.atb
        game.update(20, (1, 0), True)
        self.assertEqual((scene.model.player.atb, scene.model.enemy.atb), gauges)
        pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        self.assertTrue(game.handle_events())
        self.assertTrue(scene.paused)
        self.key(game, pygame.K_ESCAPE)
        self.assertFalse(scene.paused)
        self.assertFalse(game.pause.is_open)
        game.update(.1, (0, 0), False)
        self.assertNotEqual((scene.model.player.atb, scene.model.enemy.atb), gauges)
        self.key(game, pygame.K_ESCAPE)
        self.assertTrue(scene.paused)
        self.assertFalse(game.pause.is_open)

    def test_letterboxed_battle_commands_and_resize_use_real_mouse_coordinates(self):
        game = self.game()
        scene = self.start(game)
        self.ready(game, scene)
        pygame.event.post(pygame.event.Event(pygame.VIDEORESIZE, w=1440, h=810))
        self.assertTrue(game.handle_events())
        self.assertEqual(game.window.get_size(), (1440, 810))
        game.draw()
        self.click(game, scene.command_rects['guard'].center)
        self.assertEqual(scene.model.current_action.action, 'guard')
        self.assertTrue(game.combat.active)
        self.assertEqual(game.ui_surface.get_clip(), game.ui_surface.get_rect())

    def test_dismissal_consumes_queued_world_clicks_and_does_not_restart_battle(self):
        game = self.game()
        scene = self.start(game)
        self.action(game, scene, 'flee')
        self.advance_until(game, lambda: scene.model.ended)
        game.draw()
        button = self.point(game, scene.continue_rect.center)
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=button))
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=button))
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e, repeat=False))
        menu = self.point(game, game._hud_menu_rect().center)
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=menu))
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=menu))
        self.assertTrue(game.handle_events())
        game.update(0, (0, 0), False)
        self.assertFalse(game.combat.active)
        self.assertFalse(game.pause.is_open)
        self.assertFalse(game.map_open)
        self.assertFalse(game.quest_ui.journal_open)


if __name__ == '__main__':unittest.main()
