"""Real journey, save, and command input for permanent first-weapon skills.

The test sword is injected alongside the live gearblade so acquisition, title
validation and Continue use the same catalog for independent equipment tests.
"""
from copy import deepcopy
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

from inventory import Inventory, MAX_QUANTITY
from main import Game
from test_mill_battle_gameplay import (
    acknowledge_battle_result, click, key, read_social,
    seed_completed_mill, seed_mill_handoff,
)
from ui_style import MUTED, Painter


TEST_SWORD = 'skill_test_sword'


class CharacterSkillsGameplayTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='character-skills-gameplay-')
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.path = self.directory/'journey.json'
        self.games = []
        self.production_catalog = Inventory().catalog
        catalog = deepcopy(self.production_catalog)
        catalog['items'][TEST_SWORD] = {
            'name': 'Unawarded Test Sword',
            'description': 'A fixture for future weapon acquisition; never a live quest reward.',
            'category': 'weapons', 'equipment_slot': 'weapon',
        }
        original = Inventory.__init__

        def construct(inventory, supplied=None):
            original(inventory, catalog if supplied is None else supplied)

        patcher = patch.object(Inventory, '__init__', construct)
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        for game in self.games:
            game.opening_audio.reset();game.regional_audio.reset();game.music.stop()
        pygame.quit()

    def game(self, *, title=False, completed_mill=False):
        game = Game(window_size=(960, 640), fullscreen=False,
                    start_on_title=title, save_path=self.path,
                    settings_path=self.directory/'settings.json')
        self.games.append(game)
        game.audio.set_music(0);game.audio.set_effects(0)
        game.opening_fade = game.transfer_cooldown = 0
        pygame.event.clear()
        if completed_mill:seed_completed_mill(game)
        return game

    def snapshot(self, game):
        return deepcopy((game.character_abilities.to_dict(), game.inventory.to_dict(),
                         game.battle_rewards.to_dict(), game.attributes.to_dict(),
                         game.quests.to_dict()))

    def draw_text(self, game):
        records = []
        original = Painter.text

        def record(painter, text, *args, **kwargs):
            records.append((str(text), kwargs.get('color')))
            return original(painter, text, *args, **kwargs)

        with patch.object(Painter, 'text', record):game.draw()
        return records

    def place(self, game, point, world=None):
        world = world or game.world
        game.world = world
        for radius in (0, 8, 16, 24):
            for offset in ((0, radius), (radius, 0), (-radius, 0), (0, -radius)):
                position = pygame.Vector2(point)+offset
                if not world.can_stand(position):continue
                game.player.position.update(position)
                for delta in ((-24, 0), (24, 0), (0, 24), (0, -24)):
                    if world.can_stand(position+delta):
                        game.mill_quest._place_mira(world, position+delta)
                        break
                game.camera.reset();game.transfer_cooldown = 0
                return
        self.fail('No clear position for the story fixture.')

    def start_boar(self, game):
        """Prepare prior work, then play the authored diagnosis and entry scene."""
        seed_mill_handoff(game)
        controller = game.mill_quest
        self.place(game, controller.mira.position+(0, 28), game.town)
        key(game, pygame.K_e);read_social(game)
        for _ in range(2400):
            if not game.mill_gift.active:break
            game.update(.05, (0, 0), False)
            key(game, pygame.K_SPACE)
        self.assertFalse(game.mill_gift.active)
        for name in ('mechanism', 'race'):
            self.place(game, controller.points[name])
            key(game, pygame.K_e);read_social(game)
        self.assertTrue(controller.warned)
        self.place(game, (720, 12), game.town)
        key(game, pygame.K_e)
        self.assertEqual(game.world.data['id'], 'upstream')
        for _ in range(1000):
            if game.combat.active:break
            if game.social.active or controller.encounter_cutscene_active:read_social(game)
            else:game.update(.05, (0, 0), False)
        self.assertTrue(game.combat.active)
        self.assertEqual(game.combat.model.enemy_id, 'ridgeback_tusker')
        return game.combat.scene

    def start_bat(self, game):
        for _ in range(30):
            if not game.opening_fade and not game.transfer_cooldown:break
            game.update(.05, (0, 0), False)
        game.world = game.town
        game.player.position.update(game.combat.position+(0, 24))
        self.assertTrue(game.world.can_stand(game.player.position))
        game.player.facing = 'back';game.camera.reset()
        key(game, pygame.K_e)
        self.assertTrue(game.combat.active)
        self.assertEqual(game.combat.model.enemy_id, 'bat')
        return game.combat.scene

    def ready_player(self, game, scene):
        """Wait through production transitions, guidance, and any guest turns."""
        for _ in range(2000):
            if game.combat.transitioning:
                game.update(.05, (0, 0), False)
            elif scene.tutorial_active:
                key(game, pygame.K_SPACE)
            elif scene.model.waiting_for_player:
                game.draw()
                if 'player' in scene.model.ready_members:
                    if scene.model.ready_actor != 'player':
                        click(game, scene.party_rows['player']['row'].center)
                    if not scene.tutorial_active:
                        self.assertEqual(scene.model.ready_actor, 'player')
                        return
                else:
                    click(game, scene.command_rects['guard'].center)
            else:game.update(.05, (0, 0), False)
        self.fail('Caelan did not reach a real ready turn.')

    def advance_until(self, game, predicate):
        for _ in range(2000):
            if predicate():return
            game.update(.05, (0, 0), False)
        self.fail('The battle did not reach the expected state.')

    def unlock_dart(self, game):
        self.assertTrue(game.character_abilities.learn_ability('caelan', 'aether_dart'))
        self.assertTrue(game.save_progress())

    def test_first_story_fight_equips_blue_gift_and_guides_guard_before_aqua_attempt(self):
        game=self.game()
        self.assertIn('caelan_gearblade',self.production_catalog['items'])
        self.assertEqual(game.inventory.entries('weapons'),[])
        scene=self.start_boar(game);self.ready_player(game,scene)
        self.assertEqual([member.name for member in scene.model.party],['Caelan','Mira'])
        self.assertTrue(scene.model.weapon_equipped)
        self.assertEqual(game.inventory.quantity('caelan_gearblade'),1)
        self.assertNotIn('aether_edge',game.character_abilities.known_abilities())
        self.assertEqual(scene.model.spellblade_stage,'guard')
        self.assertEqual(scene.model.skill_actions(),[])
        click(game,scene.command_rects['guard'].center)
        self.ready_player(game,scene)
        self.assertEqual(scene.model.spellblade_stage,'first_edge')
        self.assertEqual(scene.model.skill_actions(),['aqua_edge'])
        click(game,scene.command_rects['skills'].center)
        self.assertEqual(set(scene.command_rects),{'aqua_edge','back'})
        self.assertNotIn('aether_edge',scene.command_rects)

    def test_first_weapon_grants_only_aether_edge_and_survives_continue_but_new_game_clears_it(self):
        game = self.game()
        before_rewards = game.battle_rewards.to_dict()
        self.assertTrue(game.acquire_weapon('caelan', TEST_SWORD))
        self.assertEqual(game.inventory.quantity(TEST_SWORD), 1)
        self.assertTrue(game.character_abilities.has_weapon())
        self.assertEqual(game.character_abilities.known_abilities(),
                         frozenset({'basic_magicks', 'aether_edge'}))
        self.assertNotIn('focused_strike', game.character_abilities.known_abilities())
        self.assertEqual(game.character_abilities.skill_ids(), ('aether_edge',))
        self.assertEqual(game.battle_rewards.to_dict(), before_rewards)
        saved = json.loads(self.path.read_text())
        self.assertEqual(saved['character_abilities'], game.character_abilities.to_dict())
        before = self.snapshot(game)
        resumed = self.game(title=True)
        self.assertTrue(resumed.has_saved_journey, resumed.save_error)
        self.assertTrue(resumed.begin_journey(True))
        self.assertEqual(self.snapshot(resumed), before)
        self.assertTrue(resumed.begin_journey(False, show_cinematic=False))
        self.assertEqual(resumed.inventory.quantity(TEST_SWORD), 0)
        self.assertFalse(resumed.character_abilities.has_weapon())
        self.assertEqual(resumed.character_abilities.skill_ids(), ())
        self.assertEqual(resumed.character_abilities.known_abilities(), frozenset({'basic_magicks'}))

    def test_real_skills_submenu_strikes_for_four_mp_and_settles_without_saving_a_buff(self):
        game = self.game(completed_mill=True)
        self.assertTrue(game.acquire_weapon('caelan', TEST_SWORD))
        scene = self.start_bat(game)
        self.ready_player(game, scene)
        initial_mp = game.attributes.current_mp
        initial_atb = scene.model.player.atb
        click(game, scene.command_rects['skills'].center)
        self.assertEqual(scene.command_menu, 'skills')
        self.assertEqual(set(scene.command_rects), {'aether_edge', 'back'})
        text = [text for text, _ in self.draw_text(game)]
        self.assertIn('Aether Edge', text)
        self.assertIn('4 MP · Physical and non-elemental magical sword strike.', text)
        self.assertEqual((scene.model.player.mp, scene.model.player.atb), (initial_mp, initial_atb))
        click(game, scene.command_rects['back'].center)
        self.assertEqual(scene.command_menu, 'root')
        click(game, scene.command_rects['skills'].center)
        click(game, scene.command_rects['aether_edge'].center)
        self.assertEqual(scene.model.current_action.action, 'aether_edge')
        self.assertEqual((scene.model.player.mp, scene.model.player.atb), (initial_mp-4, 0))
        self.assertEqual(game.attributes.current_mp, initial_mp)
        self.assertEqual(scene.model.player.aether_edge_hits, 0)
        enemy_hp = scene.model.enemy.hp
        self.advance_until(game, lambda: scene.model.current_action is not None and scene.model.current_action.resolved)
        self.assertLess(scene.model.enemy.hp, enemy_hp)
        self.assertEqual(scene.model.player.aether_edge_hits, 0)
        self.assertNotIn('Edge · 3 strikes', [text for text, _ in self.draw_text(game)])
        self.ready_player(game, scene)
        click(game, scene.command_rects['flee'].center)
        self.advance_until(game, lambda: scene.model.ended)
        self.assertEqual(scene.model.player.aether_edge_hits, 0)
        acknowledge_battle_result(game, scene)
        self.assertEqual(game.attributes.current_mp, initial_mp-4)
        saved = json.loads(self.path.read_text())
        self.assertNotIn('aether_edge_hits', json.dumps(saved))
        resumed = self.game(title=True)
        self.assertTrue(resumed.begin_journey(True))
        self.assertIn('aether_edge', resumed.character_abilities.known_abilities())
        self.assertEqual(resumed.attributes.current_mp, initial_mp-4)

    def test_unequip_preserves_permanent_skill_and_save_but_disables_its_battle_use(self):
        game = self.game(completed_mill=True)
        self.assertTrue(game.acquire_weapon('caelan', TEST_SWORD))
        self.assertTrue(game.equip_weapon('caelan', None))
        self.assertEqual(game.inventory.quantity(TEST_SWORD), 1)
        self.assertIn('aether_edge', game.character_abilities.known_abilities())
        resumed = self.game(title=True)
        self.assertTrue(resumed.begin_journey(True))
        self.assertFalse(resumed.character_abilities.has_weapon())
        self.assertEqual(resumed.character_abilities.skill_ids(), ('aether_edge',))
        scene = self.start_bat(resumed)
        self.ready_player(resumed, scene)
        before = scene.model.player.mp, scene.model.player.atb
        click(resumed, scene.command_rects['skills'].center)
        self.assertEqual(scene.command_menu, 'root')
        self.assertEqual(scene.model.action_reason('aether_edge'), 'Requires a weapon.')
        self.assertFalse(scene.model.choose_action('aether_edge'))
        self.assertEqual((scene.model.player.mp, scene.model.player.atb), before)

    def test_rejected_grants_and_equips_do_not_change_progress_or_checkpoint(self):
        game = self.game(completed_mill=True)
        before = self.snapshot(game)
        saved = self.path.read_bytes()
        with patch.object(game, 'save_progress', wraps=game.save_progress) as checkpoint:
            for character, item in (('missing', TEST_SWORD), ('caelan', 'missing'),
                                    ('caelan', 'aether_diamond'), ('caelan', None)):
                with self.subTest(character=character, item=item):
                    self.assertFalse(game.acquire_weapon(character, item))
                    if item is not None:self.assertFalse(game.equip_weapon(character, item))
                    self.assertEqual(self.snapshot(game), before)
            self.assertFalse(game.equip_weapon('caelan', TEST_SWORD))
            with patch.object(game.inventory, 'add', return_value=False):
                self.assertFalse(game.acquire_weapon('caelan', TEST_SWORD))
            checkpoint.assert_not_called()
        self.assertEqual(self.snapshot(game), before)
        self.assertEqual(self.path.read_bytes(), saved)
        self.assertTrue(game.inventory.add(TEST_SWORD, MAX_QUANTITY))
        before = self.snapshot(game)
        self.assertFalse(game.acquire_weapon('caelan', TEST_SWORD))
        self.assertEqual(self.snapshot(game), before)

    def test_insufficient_mp_keeps_the_skill_submenu_and_all_gauges_unchanged(self):
        game = self.game(completed_mill=True)
        self.assertTrue(game.acquire_weapon('caelan', TEST_SWORD))
        self.assertTrue(game.attributes.set_current(mp=3))
        scene = self.start_bat(game)
        self.ready_player(game, scene)
        click(game, scene.command_rects['skills'].center)
        before = (scene.model.player.mp, scene.model.player.atb, scene.model.enemy.atb)
        click(game, scene.command_rects['aether_edge'].center)
        self.assertEqual(scene.command_menu, 'skills')
        self.assertIn('Not enough MP.', [text for text, _ in self.draw_text(game)])
        self.assertIsNone(scene.model.current_action)
        self.assertEqual((scene.model.player.mp, scene.model.player.atb, scene.model.enemy.atb), before)
        self.assertEqual(scene.model.player.aether_edge_hits, 0)

    def test_learned_dart_remains_a_usable_root_command_when_unarmed(self):
        game = self.game(completed_mill=True)
        self.unlock_dart(game)
        self.assertTrue(game.equip_weapon('caelan', None))
        self.assertIn('aether_dart', game.character_abilities.known_abilities())
        scene = self.start_bat(game)
        self.ready_player(game, scene)
        self.assertIn('aether_dart', scene._command_actions())
        for _ in scene._command_actions():
            if 'aether_dart' in scene.command_rects:break
            key(game, pygame.K_DOWN)
            game.draw()
        self.assertIn('aether_dart', scene.command_rects)
        self.assertEqual(scene.model.command_reason('skills'), 'Requires a weapon.')
        initial_mp = scene.model.player.mp
        click(game, scene.command_rects['aether_dart'].center)
        self.assertEqual(scene.model.current_action.action, 'aether_dart')
        self.assertEqual(scene.model.player.mp, initial_mp-4)
        self.advance_until(game, lambda: scene.model.current_action is not None
                           and scene.model.current_action.resolved)
        self.assertGreater(scene.model.current_action.damage, 0)

    def test_active_battle_refuses_weapon_grants_and_equipment_changes_without_costs(self):
        game = self.game(completed_mill=True)
        self.assertTrue(game.acquire_weapon('caelan', TEST_SWORD))
        scene = self.start_bat(game)
        self.ready_player(game, scene)
        before = self.snapshot(game)
        gauges = scene.model.player.mp, scene.model.player.atb, scene.model.enemy.atb
        with patch.object(game, 'save_progress', wraps=game.save_progress) as checkpoint:
            self.assertFalse(game.acquire_weapon('caelan', TEST_SWORD))
            self.assertFalse(game.equip_weapon('caelan', None))
            self.assertFalse(game.equip_weapon('caelan', TEST_SWORD))
            checkpoint.assert_not_called()
        self.assertEqual(self.snapshot(game), before)
        self.assertEqual((scene.model.player.mp, scene.model.player.atb, scene.model.enemy.atb), gauges)
        self.assertEqual(scene.model.action_reason('aether_edge'), '')

    def test_title_and_opening_cinematic_refuse_loadout_changes(self):
        game = self.game(title=True)
        before = self.snapshot(game)
        self.assertFalse(game.acquire_weapon('caelan', TEST_SWORD))
        self.assertFalse(game.equip_weapon('caelan', TEST_SWORD))
        self.assertFalse(game.equip_weapon('caelan', None))
        self.assertEqual(self.snapshot(game), before)
        self.assertFalse(self.path.exists())
        self.assertTrue(game.begin_journey(False))
        self.assertTrue(game.opening_cinematic.active)
        before = self.snapshot(game)
        self.assertFalse(game.acquire_weapon('caelan', TEST_SWORD))
        self.assertFalse(game.equip_weapon('caelan', None))
        self.assertEqual(self.snapshot(game), before)

    def test_missing_skill_state_defaults_to_unarmed_without_losing_receipts_or_items(self):
        game = self.game(completed_mill=True)
        self.unlock_dart(game)
        self.assertTrue(game.acquire_weapon('caelan', TEST_SWORD))
        legacy = json.loads(self.path.read_text())
        del legacy['character_abilities']
        raw = json.dumps(legacy)
        self.path.write_text(raw)
        resumed = self.game(title=True)
        self.assertTrue(resumed.has_saved_journey, resumed.save_error)
        self.assertEqual(self.path.read_text(), raw)
        self.assertTrue(resumed.begin_journey(True))
        self.assertEqual(resumed.inventory.to_dict(), legacy['inventory'])
        self.assertEqual(resumed.battle_rewards.to_dict(), legacy['battle_rewards'])
        self.assertFalse(resumed.character_abilities.has_weapon())
        self.assertNotIn('aether_dart', resumed.character_abilities.known_abilities())
        self.assertNotIn('aether_edge', resumed.character_abilities.known_abilities())
        self.assertEqual(resumed.character_abilities.skill_ids(), ())

    def test_malformed_skill_state_is_rejected_on_title_without_overwriting_the_journey(self):
        game = self.game(completed_mill=True)
        self.assertTrue(game.acquire_weapon('caelan', TEST_SWORD))
        saved = json.loads(self.path.read_text())
        malformed = [None, {}, {'version': True, 'characters': {}}]
        unowned = deepcopy(saved['character_abilities'])
        unowned['characters']['caelan']['equipped_weapon'] = 'missing_weapon'
        malformed.append(unowned)
        no_history = deepcopy(saved['character_abilities'])
        no_history['characters']['caelan']['first_weapon_acquired'] = False
        malformed.append(no_history)
        for state in malformed:
            with self.subTest(state=state):
                data = deepcopy(saved);data['character_abilities'] = state
                raw = json.dumps(data);self.path.write_text(raw)
                resumed = self.game(title=True)
                self.assertFalse(resumed.has_saved_journey)
                self.assertIsNotNone(resumed.save_error)
                self.assertFalse(resumed.begin_journey(True))
                self.assertEqual(self.path.read_text(), raw)
                self.assertEqual(resumed.character_abilities.known_abilities(),
                                 frozenset({'basic_magicks'}))
                self.assertFalse(resumed.character_abilities.has_weapon())
                self.assertEqual(resumed.inventory.entries(), [])


if __name__ == '__main__':unittest.main()
