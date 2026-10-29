"""Lattice rewards, crystal purchases, saves and actual paused-game input."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
from aether_lattice import AetherLattice, LatticeBoard
from lattice_progression import LatticeProgression
from main import Game
from quests import OPENING_QUEST


class LatticeGameplayTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='lattice-gameplay-test-')
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.path = self.directory/'journey.json'

    def tearDown(self):pygame.quit()

    def game(self, title=False):
        game = Game(fullscreen=False, start_on_title=title, save_path=self.path,
                    settings_path=self.directory/'settings.json')
        game.audio.set_music(0);game.audio.set_effects(0)
        pygame.event.clear()
        return game

    def snapshot(self, game):
        return (game.lattice.to_dict(), game.inventory.to_dict(), game.attributes.to_dict(),
                {key: game.attributes.value(key) for key in game.attributes.definitions})

    def first_hp(self, game):
        self.assertTrue(game.award_battle_rewards('first_hp_reward', {'caelan': 20}, {'aether_emerald': 1}))
        self.assertTrue(game.move_lattice('hp_01'))
        self.assertTrue(game.activate_lattice('hp_01'))

    def key(self, game, value):
        for kind in (pygame.KEYDOWN, pygame.KEYUP):
            pygame.event.post(pygame.event.Event(kind, key=value, repeat=False))
        self.assertTrue(game.handle_events())

    def point(self, game, logical):
        width, height = game.window.get_size();scale = max(1, min(width//480, height//320))
        return (round((width-480*scale)//2+logical[0]*scale),
                round((height-320*scale)//2+logical[1]*scale))

    def click(self, game, logical):
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            pygame.event.post(pygame.event.Event(kind, button=1, pos=self.point(game, logical)))
        self.assertTrue(game.handle_events())

    def open_lattice(self, game):
        self.key(game, pygame.K_ESCAPE)
        for _ in range(game.pause.options.index('Aether Lattice')):self.key(game, pygame.K_DOWN)
        self.key(game, pygame.K_RETURN)
        self.assertTrue(game.lattice_ui.is_open)
        self.assertEqual(game.pause.overlay, 'lattice')

    def select(self, game, identifier):
        # Camera placement is fixture setup; selection itself uses real input.
        game.lattice_ui.center_on(identifier, immediate=True)
        game.draw()
        self.click(game, game.lattice_ui.node_position(identifier))
        self.assertEqual(game.lattice_ui.selected, identifier)
        for _ in range(12):game.update(1/60)
        game.draw()

    def test_real_new_game_has_no_sample_rewards_and_resets_preview_progress(self):
        game = self.game()
        self.first_hp(game)
        self.assertEqual(game.attributes.value('hp'), 240)
        self.assertTrue(game.begin_journey())
        self.assertEqual(game.lattice.rank(), 1)
        self.assertEqual(game.lattice.steps(), 0)
        self.assertEqual(game.lattice.rp_progress(), (0, 20))
        self.assertEqual(game.lattice.state()['position'], 'origin')
        self.assertEqual(game.lattice.state()['activated'], [])
        self.assertEqual(game.attributes.value('hp'), 140)
        self.assertEqual(game.attributes.current_hp, 140)
        self.assertTrue(all(game.inventory.quantity(key) == 0 for key in game.lattice.board.crystals))
        self.assertEqual(game.quests.status(OPENING_QUEST), 'available')
        self.assertEqual(game.opening.stage, 'wake')

    def test_acceptance_flow_checkpoints_once_without_restoring_health(self):
        game = self.game()
        self.assertTrue(game.award_battle_rewards('first_battle', {'caelan': 20}, {'aether_emerald': 1}))
        self.assertEqual((game.lattice.rank(), game.lattice.steps()), (2, 1))
        self.assertTrue(game.move_lattice('hp_01'))
        self.assertEqual((game.lattice.rank(), game.lattice.steps()), (2, 0))
        self.assertEqual(game.attributes.value('hp'), 140)
        self.assertTrue(game.activate_lattice('hp_01'))
        self.assertEqual(game.attributes.value('hp'), 240)
        self.assertEqual(game.attributes.base_value('hp'), 140)
        self.assertEqual(game.attributes.current_hp, 140)
        self.assertEqual(game.inventory.quantity('aether_emerald'), 0)
        committed = self.snapshot(game)
        self.assertFalse(game.activate_lattice('hp_01'))
        self.assertEqual(self.snapshot(game), committed)
        saved = json.loads(self.path.read_text())
        self.assertEqual(saved['aether_lattice'], game.lattice.to_dict())
        self.assertEqual(saved['character_attributes']['attributes']['hp'], 140)
        for _ in range(2):
            restored = self.game(title=True)
            self.assertTrue(restored.has_saved_journey)
            self.assertEqual(restored.attributes.value('hp'), 140)
            self.assertTrue(restored.begin_journey(True))
            self.assertEqual(self.snapshot(restored), committed)

    def test_continue_validates_resources_against_derived_maximum(self):
        game = self.game();self.first_hp(game)
        self.assertTrue(game.attributes.set_current(hp=155, mp=12))
        self.assertTrue(game.save_progress())
        restored = self.game(title=True)
        self.assertTrue(restored.has_saved_journey)
        self.assertTrue(restored.begin_journey(True))
        self.assertEqual(restored.attributes.base_value('hp'), 140)
        self.assertEqual(restored.attributes.value('hp'), 240)
        self.assertEqual(restored.attributes.current_hp, 155)
        self.assertEqual(restored.attributes.current_mp, 12)

    def test_continue_migrates_a_real_starter_journey_without_losing_growth_or_resources(self):
        game = self.game()
        legacy_path = Path(__file__).resolve().parents[1]/'assets/progression/aether_lattice_v1.json'
        legacy = AetherLattice(LatticeBoard(json.loads(legacy_path.read_text())))
        progression = LatticeProgression(legacy, game.inventory, {'caelan': game.attributes})
        self.assertTrue(progression.award_battle_rewards('legacy_battle', {'caelan': 2000},
                                                       {'aether_emerald': 2, 'aether_diamond': 2}))
        for identifier in ('hp_01', 'mend_01', 'brace_01'):
            self.assertTrue(progression.move(identifier))
            self.assertTrue(progression.activate(identifier))
        self.assertTrue(game.attributes.set_current(hp=155, mp=12))
        game.lattice, game.lattice_progression = legacy, progression
        self.assertTrue(game.save_progress())
        original_bytes = self.path.read_bytes()
        expected_lattice = copy.deepcopy(legacy.to_dict())
        self.assertEqual(expected_lattice['board_version'], 1)
        expected_lattice['board_version'] = 3
        expected_lattice['version'] = 2
        for state in expected_lattice['characters'].values():
            state['legacy_activated'] = list(state['activated'])
        expected_attributes, expected_inventory = game.attributes.to_dict(), game.inventory.to_dict()
        expected_steps, expected_rank = legacy.steps(), legacy.rank()
        for _ in range(2):
            restored = self.game(title=True)
            self.assertTrue(restored.has_saved_journey)
            self.assertEqual(self.path.read_bytes(), original_bytes)
            self.assertTrue(restored.begin_journey(True))
            self.assertEqual(restored.lattice.to_dict(), expected_lattice)
            self.assertEqual(restored.attributes.to_dict(), expected_attributes)
            self.assertEqual(restored.inventory.to_dict(), expected_inventory)
            self.assertEqual(restored.lattice.steps(), expected_steps)
            self.assertEqual(restored.lattice.rank(), expected_rank)
            self.assertEqual(restored.lattice.learned_abilities(), ['basic_magicks', 'brace', 'mend'])
            self.assertEqual((restored.attributes.value('hp'), restored.attributes.current_hp,
                              restored.attributes.current_mp), (160, 155, 12))
            self.assertFalse(restored.award_battle_rewards('legacy_battle', {'caelan': 2000},
                                                          {'aether_emerald': 2}))
            self.assertTrue(restored.save_progress())
            original_bytes = self.path.read_bytes()
            self.assertEqual(json.loads(original_bytes)['aether_lattice']['board_version'], 3)

    def test_multi_rank_rewards_are_idempotent_but_new_battle_attempts_are_valid(self):
        game = self.game()
        self.assertTrue(game.award_battle_rewards('encounter_attempt_1', {'caelan': 75}, {'aether_emerald': 2}))
        self.assertEqual((game.lattice.rank(), game.lattice.steps()), (4, 3))
        self.assertEqual(game.lattice.rp_progress(), (0, 35))
        prior = self.snapshot(game)
        self.assertFalse(game.award_battle_rewards('encounter_attempt_1', {'caelan': 75}, {'aether_emerald': 2}))
        self.assertEqual(self.snapshot(game), prior)
        restored = self.game(title=True)
        self.assertTrue(restored.begin_journey(True))
        self.assertFalse(restored.award_battle_rewards('encounter_attempt_1', {'caelan': 75}, {'aether_emerald': 2}))
        self.assertEqual(self.snapshot(restored), prior)
        self.assertTrue(restored.award_battle_rewards('encounter_attempt_2', {'caelan': 75}, {'aether_emerald': 2}))
        self.assertEqual((restored.lattice.rank(), restored.lattice.steps()), (6, 5))
        self.assertEqual(restored.inventory.quantity('aether_emerald'), 4)

    def test_rp_only_and_loot_only_rewards_have_no_empty_bundle_failure(self):
        game = self.game()
        self.assertTrue(game.award_battle_rewards('rp_only', {'caelan': 20}, {}))
        self.assertEqual((game.lattice.rank(), game.lattice.steps()), (2, 1))
        self.assertEqual(game.inventory.entries('items'), [])
        self.assertTrue(game.award_battle_rewards('loot_only', {}, {'aether_emerald': 2}))
        self.assertEqual((game.lattice.rank(), game.lattice.steps()), (2, 1))
        self.assertEqual(game.inventory.quantity('aether_emerald'), 2)
        before = self.snapshot(game)
        self.assertFalse(game.award_battle_rewards('empty_reward', {}, {}))
        self.assertEqual(self.snapshot(game), before)

    def test_failed_checkpoint_preserves_complete_live_activation_for_retry(self):
        game = self.game()
        self.assertTrue(game.award_battle_rewards('save_retry', {'caelan': 20}, {'aether_emerald': 1}))
        self.assertTrue(game.move_lattice('hp_01'))
        saved_before = self.path.read_bytes()
        with patch('save_game.os.replace', side_effect=OSError('disk unavailable')):
            self.assertTrue(game.activate_lattice('hp_01'))
        self.assertEqual(game.attributes.value('hp'), 240)
        self.assertEqual(game.inventory.quantity('aether_emerald'), 0)
        self.assertIn('hp_01', game.lattice.state()['activated'])
        self.assertEqual(self.path.read_bytes(), saved_before)
        self.assertIsNotNone(game.save_error)
        self.assertTrue(game.save_progress())
        restored = self.game(title=True)
        self.assertTrue(restored.begin_journey(True))
        self.assertEqual(self.snapshot(restored), self.snapshot(game))

    def test_wrong_crystal_and_invalid_rewards_never_partially_change_progress(self):
        game = self.game()
        self.assertTrue(game.award_battle_rewards('sapphire_only', {'caelan': 20}, {'aether_sapphire': 1}))
        self.assertTrue(game.move_lattice('hp_01'))
        before = self.snapshot(game)
        self.assertFalse(game.activate_lattice('hp_01'))
        self.assertIn('Emerald', game.lattice_activation_reason('hp_01'))
        self.assertEqual(self.snapshot(game), before)
        invalid = [({'caelan': 20, 'unknown': 1}, {'aether_emerald': 1}),
                   ({'caelan': 20}, {'unknown_item': 1}),
                   ({'caelan': 20}, {'halden_medicine': 1}),
                   ({'caelan': -1}, {'aether_emerald': 1}),
                   ({'caelan': True}, {'aether_emerald': 1}),
                   ({'caelan': 20}, {'aether_emerald': -1})]
        for index, (awards, drops) in enumerate(invalid):
            with self.subTest(index=index):
                self.assertFalse(game.award_battle_rewards('invalid_'+str(index), awards, drops))
                self.assertEqual(self.snapshot(game), before)

    def test_legacy_values_migrate_into_base_without_inventing_lattice_progress(self):
        game = self.game()
        self.assertTrue(game.accept_quest(OPENING_QUEST))
        game.social.flags.add('legacy_lattice_journey')
        attributes = game.attributes.to_dict()
        attributes['attributes'].update(hp=170, mag=14, spr=16)
        attributes.update(current_hp=160, current_mp=21)
        self.assertTrue(game.attributes.restore(attributes))
        self.assertTrue(game.save_progress())
        legacy = json.loads(self.path.read_text())
        legacy.pop('aether_lattice')
        legacy['character_attributes']['version'] = 2
        self.path.write_text(json.dumps(legacy))
        restored = self.game(title=True)
        self.assertTrue(restored.has_saved_journey)
        self.assertTrue(restored.begin_journey(True))
        self.assertEqual(restored.attributes.base_value('hp'), 170)
        self.assertEqual(restored.attributes.value('hp'), 170)
        self.assertEqual(restored.attributes.current_hp, 160)
        self.assertEqual(restored.attributes.value('mag'), 14)
        self.assertEqual(restored.attributes.value('spr'), 16)
        self.assertEqual(restored.lattice.rank(), 1)
        self.assertEqual(restored.lattice.steps(), 0)
        self.assertEqual(restored.lattice.state()['activated'], [])
        self.assertEqual(restored.quests.to_dict(), legacy['quests'])
        self.assertEqual(restored.inventory.to_dict(), legacy['inventory'])
        self.assertEqual(sorted(restored.social.flags), legacy['dialogue_flags'])

    def test_invalid_combined_save_preserves_existing_file_and_fresh_title_state(self):
        game = self.game();self.first_hp(game)
        self.assertTrue(game.attributes.set_current(hp=155))
        self.assertTrue(game.save_progress())
        saved = json.loads(self.path.read_text())
        missing = copy.deepcopy(saved);missing.pop('aether_lattice')
        overfull = copy.deepcopy(saved);overfull['character_attributes']['current_hp'] = 241
        for bad in (missing, overfull):
            with self.subTest(missing='aether_lattice' not in bad):
                raw = json.dumps(bad);self.path.write_text(raw)
                restored = self.game(title=True)
                self.assertFalse(restored.has_saved_journey)
                self.assertFalse(restored.begin_journey(True))
                self.assertEqual(self.path.read_text(), raw)
                self.assertEqual(restored.attributes.value('hp'), 140)
                self.assertEqual(restored.lattice.rank(), 1)

    def test_real_menu_clicks_context_actions_and_preserves_world_and_queued_clicks(self):
        game = self.game()
        self.assertTrue(game.award_battle_rewards('menu_test', {'caelan': 20}, {'aether_emerald': 1}))
        self.open_lattice(game)
        before = self.snapshot(game)
        clock, position = game.elapsed_ms, game.player.position.copy()
        self.select(game, 'hp_01');game.draw()
        self.assertEqual(self.snapshot(game), before)
        game.update(2, (1, 0), True)
        self.assertEqual(game.elapsed_ms, clock)
        self.assertEqual(game.player.position, position)
        ui = game.lattice_ui
        preview = ui.action_preview()
        self.assertEqual((preview['action'], preview['node']), ('move', 'hp_01'))
        self.assertIn('1 Step', ' '.join(preview['lines']))
        saved = self.path.read_bytes()
        for key in (pygame.K_m, pygame.K_a, pygame.K_RETURN, pygame.K_KP_ENTER,
                    pygame.K_TAB, pygame.K_PLUS, pygame.K_MINUS, pygame.K_f, pygame.K_0):
            self.key(game, key)
        self.assertEqual(self.snapshot(game), before)
        self.assertEqual(self.path.read_bytes(), saved)
        self.assertEqual(ui.selected, 'hp_01')
        point = self.point(game, ui.action_rect.center)
        # Repeated downs from a held button must not activate the new current node.
        for _ in range(3):
            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point))
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=point))
        self.assertTrue(game.handle_events())
        self.assertEqual(game.lattice.state()['position'], 'hp_01')
        self.assertEqual(game.lattice.steps(), 0)
        self.assertEqual(game.attributes.value('hp'), 140)
        self.assertEqual(game.inventory.quantity('aether_emerald'), 1)
        game.draw()
        after_move = self.snapshot(game)
        self.assertEqual(ui.action_preview()['action'], 'activate')
        self.key(game, pygame.K_a);self.key(game, pygame.K_RETURN)
        self.assertEqual(self.snapshot(game), after_move)
        self.click(game, ui.action_rect.center)
        self.assertEqual(game.attributes.value('hp'), 240)
        self.assertEqual(game.attributes.current_hp, 140)
        self.assertEqual(game.inventory.quantity('aether_emerald'), 0)
        self.assertIsNone(ui.action_preview())
        after_activation = self.snapshot(game)
        self.assertEqual(json.loads(self.path.read_text())['aether_lattice'], game.lattice.to_dict())
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, repeat=False))
        point = self.point(game, game.pause.rows[0].center)
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            pygame.event.post(pygame.event.Event(kind, button=1, pos=point))
        self.assertTrue(game.handle_events())
        self.assertFalse(game.lattice_ui.is_open)
        self.assertTrue(game.pause.is_open)
        self.assertIsNone(game.pause.overlay)
        self.assertEqual(self.snapshot(game), after_activation)

    def test_paused_game_updates_cursor_camera_and_pulse_without_advancing_world(self):
        game = self.game()
        self.open_lattice(game)
        screen = game.lattice_ui
        before = self.snapshot(game)
        saved = self.path.read_bytes()
        world_time, player = game.elapsed_ms, game.player.position.copy()
        npcs = [npc.position.copy() for npc in game.world.npcs]
        cursor = screen.cursor_position.copy()
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT, repeat=False))
        self.assertTrue(game.handle_events())
        for _ in range(24):game.update(1/60, (1, 0), True)
        self.assertTrue(screen.navigating)
        self.assertGreater(screen.cursor_position.x, cursor.x)
        selected = min(screen.board.nodes, key=lambda identifier:
                       pygame.Vector2(screen.board.nodes[identifier]['position']).distance_squared_to(screen.cursor_position))
        pygame.event.post(pygame.event.Event(pygame.KEYUP, key=pygame.K_RIGHT))
        self.assertTrue(game.handle_events())
        self.assertFalse(screen.navigating)
        self.assertEqual(screen.selected, selected)
        pan = screen.pan.copy()
        game.update(.04, (1, 0), True)
        self.assertNotEqual(screen.pan, pan)
        for _ in range(12):game.update(1/60, (1, 0), True)
        self.assertLess(screen.node_position(selected).distance_to(screen.map_rect.center), .001)
        strength = screen.pulse_strength
        game.update(.2, (1, 0), True)
        self.assertNotAlmostEqual(screen.pulse_strength, strength)
        self.assertEqual(game.elapsed_ms, world_time)
        self.assertEqual(game.player.position, player)
        self.assertEqual([npc.position for npc in game.world.npcs], npcs)
        self.assertEqual(self.snapshot(game), before)
        self.assertEqual(self.path.read_bytes(), saved)

    def test_real_paused_zoom_changes_camera_without_changing_world_or_journey(self):
        game = self.game()
        self.open_lattice(game)
        screen = game.lattice_ui
        before = self.snapshot(game)
        saved = self.path.read_bytes()
        world_time, player = game.elapsed_ms, game.player.position.copy()
        npcs = [npc.position.copy() for npc in game.world.npcs]
        initial = screen.zoom
        point = self.point(game, screen.map_rect.center)
        pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=point, rel=(0, 0), buttons=(0, 0, 0)))
        pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=1))
        self.assertTrue(game.handle_events())
        target = screen.target_zoom
        self.assertGreater(target, initial)
        self.assertEqual(screen.zoom, initial)
        game.update(screen.ZOOM_DURATION/3, (1, 0), True)
        self.assertGreater(screen.zoom, initial)
        self.assertLess(screen.zoom, target)
        for _ in range(12):game.update(1/60, (1, 0), True)
        self.assertAlmostEqual(screen.zoom, target)
        pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=-3))
        self.assertTrue(game.handle_events())
        for _ in range(12):game.update(1/60)
        self.assertLess(screen.zoom, initial)
        zoom, pan = screen.zoom, screen.pan.copy()
        for key in (pygame.K_PLUS, pygame.K_MINUS, pygame.K_EQUALS,
                    pygame.K_KP_PLUS, pygame.K_KP_MINUS, pygame.K_f,
                    pygame.K_0, pygame.K_KP0):self.key(game, key)
        for _ in range(12):game.update(1/60)
        self.assertEqual(screen.zoom, zoom)
        self.assertEqual(screen.pan, pan)
        self.assertEqual(screen.selected, 'origin')
        self.assertEqual(game.elapsed_ms, world_time)
        self.assertEqual(game.player.position, player)
        self.assertEqual([npc.position for npc in game.world.npcs], npcs)
        self.assertEqual(self.snapshot(game), before)
        self.assertEqual(self.path.read_bytes(), saved)

    def test_navigation_does_not_resume_after_focus_loss_or_closing_overlay(self):
        game = self.game()
        self.open_lattice(game)
        screen = game.lattice_ui
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT, repeat=False))
        self.assertTrue(game.handle_events())
        game.update(.1)
        pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertTrue(game.handle_events())
        self.assertFalse(screen.navigating)
        cursor = screen.cursor_position.copy()
        game.update(.5)
        self.assertEqual(screen.cursor_position, cursor)
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT, repeat=False))
        self.assertTrue(game.handle_events())
        self.assertTrue(screen.navigating)
        self.key(game, pygame.K_ESCAPE)
        self.assertFalse(screen.is_open)
        self.assertFalse(screen.navigating)
        self.assertTrue(game.pause.is_open)
        game.pause.selected = game.pause.options.index('Aether Lattice')
        self.key(game, pygame.K_RETURN)
        game.update(.2)
        self.assertTrue(screen.is_open)
        self.assertFalse(screen.navigating)
        self.assertEqual(screen.selected, 'origin')
        self.assertEqual(screen.cursor_position, pygame.Vector2(screen.board.nodes['origin']['position']))


if __name__ == '__main__':unittest.main()
