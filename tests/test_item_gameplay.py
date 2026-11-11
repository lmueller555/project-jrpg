"""Item menus and complete reward transactions through the actual Game owner."""
from copy import deepcopy
import json
import os
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from main import Game
from inventory import Inventory, MAX_QUANTITY
from cave_random_encounters import CaveRandomEncounters
from post_battle import battle_reward_definition, valid_pending_snapshot
from enemy_loot import encounter_drops
from test_mill_battle_gameplay import key, click, seed_completed_mill, wait_for_spoils


class ItemGameplayTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        self.addCleanup(pygame.quit)
        self.path = Path(folder.name)/'journey.json'
        self.settings = Path(folder.name)/'settings.json'
        self.game = Game(fullscreen=False, start_on_title=False, save_path=self.path, settings_path=self.settings)
        self.game.audio.set_music(0);self.game.audio.set_effects(0)
        seed_completed_mill(self.game)
        if 'mira' not in self.game.party.members:self.game.party.recruit('mira')
        self.game.party.set_available('mira', True)
        self.assertTrue(self.game.party.select(('caelan', 'mira')))
        self.game.attributes.set_current(hp=40, mp=0)

    def load(self):
        game = Game(fullscreen=False, start_on_title=True, save_path=self.path, settings_path=self.settings)
        game.audio.set_music(0);game.audio.set_effects(0)
        self.assertTrue(game.has_saved_journey, game.save_error)
        self.assertTrue(game.begin_journey(True), game.save_error)
        return game

    def ready(self, actor='player'):
        model = self.game.combat.model
        model.phase = 'charging';model.current_action = None
        for member in (*model.party, *model.enemies):member.atb = 0.
        model.combatant(actor).atb = 1.;model.update(0)
        self.game.draw()

    def click_command(self, command):
        scene = self.game.combat.scene
        actions = scene._command_actions()
        for _ in range(len(actions)+1):
            self.game.draw()
            if command in scene.command_rects:break
            key(self.game, pygame.K_DOWN)
        self.assertIn(command, scene.command_rects)
        click(self.game, scene.command_rects[command].center)

    def cave(self, *, potion_full=False):
        game = self.game
        if potion_full:game.inventory.add('potion', MAX_QUANTITY-game.inventory.quantity('potion'))
        if not game.character_abilities.has_weapon():game.character_abilities.acquire_weapon('caelan', 'caelan_gearblade')
        game.character_abilities.learn_ability('caelan', 'aqua_edge')
        self.assertTrue(game.cave_lesson.restore({'version': 1, 'resonance_seen': True,
                                                'battle_cleared': True, 'deferred': False}))
        # Pick a real authored formation with a Potion roll to cover item/cap accounting.
        for seed in range(100):
            counter = CaveRandomEncounters(seed)
            ticket = counter.advance(1000, (1680, 970))
            if ticket and encounter_drops('cave', ticket, ticket['receipt'], {}).get('potion'):break
        else:self.fail('No Potion-bearing encounter found')
        game.world = game._scene_by_id('sanctuary_cave')
        game.player.position.update(ticket['position']);game.camera.reset()
        self.assertTrue(game.cave_random_encounters.restore(counter.to_dict()))
        self.assertTrue(game.combat.start_cave(ticket))
        for _ in range(120):
            game.update(.05, (0, 0), False);game.draw()
            if game.combat.model is not None and not game.combat.transitioning:break
        self.assertIsNotNone(game.combat.model)
        return ticket

    def victory(self):
        owner = self.game.combat
        for enemy in owner.model.enemies:enemy.hp = 0
        owner.model._result('victory')
        self.assertTrue(owner._begin_victory())
        data = json.loads(self.path.read_text())
        self.assertTrue(valid_pending_snapshot(owner.snapshot(), data))
        return owner.snapshot()

    def test_field_inventory_keyboard_mouse_and_rest_kit_remain_safe(self):
        game = self.game
        game.inventory_ui.open();game.inventory_ui.category_index = 2
        game.inventory_ui.selected = 'potion';game.draw()
        click(game, game.inventory_ui.use_rect.center);game.draw()
        self.assertEqual(game.inventory_ui._use_item_id, 'potion')
        key(game, pygame.K_ESCAPE)
        self.assertTrue(game.inventory_ui.is_open)
        self.assertEqual(game.inventory.quantity('potion'), 5)
        key(game, pygame.K_RETURN);game.draw()
        click(game, game.inventory_ui.target_rects['caelan'].center)
        self.assertEqual(game.attributes.current_hp, 140)
        self.assertEqual(game.inventory.quantity('potion'), 4)
        key(game, pygame.K_ESCAPE)
        game.inventory_ui.selected = 'rest_kit'
        key(game, pygame.K_RETURN)
        self.assertIsNone(game.inventory_ui._use_item_id)
        self.assertEqual(game.inventory.quantity('rest_kit'), 3)

    def test_actual_battle_menu_heals_then_smoke_commits_both_costs_once(self):
        game = self.game
        game.player.position.update(game.combat.position+(0, 24))
        self.assertTrue(game.combat.interact(random.Random(4)))
        game.combat.transition = None
        self.ready();self.click_command('items');self.click_command('item:potion')
        self.assertEqual(game.combat.scene.command_menu, 'item_targets')
        self.click_command('ally:player')
        game.update(.5, (0, 0), False);game.draw()
        self.assertEqual(game.combat.model.player.hp, 140)
        self.assertEqual(game.attributes.current_hp, 40, 'Battle resources remain local until settlement')
        self.assertEqual(game.inventory.quantity('potion'), 5)
        game.update(.5, (0, 0), False)
        self.ready();self.click_command('items');self.click_command('item:smoke_bomb')
        game.update(1., (0, 0), False)
        self.assertEqual(game.combat.model.phase, 'fled')
        game.combat.scene.dismissed = True;game.update(0, (0, 0), False)
        self.assertFalse(game.combat.active)
        self.assertEqual(game.attributes.current_hp, 140)
        self.assertEqual((game.inventory.quantity('potion'), game.inventory.quantity('smoke_bomb')), (4, 2))
        self.assertEqual(self.load().inventory.quantity('smoke_bomb'), 2)

    def test_victory_costs_rolls_and_continue_are_atomic_and_do_not_reroll(self):
        ticket = self.cave();game = self.game;model = game.combat.model
        self.ready();self.assertTrue(model.choose_item('potion', 'player'));model.update(1.)
        self.ready();self.assertTrue(model.choose_item('ether', 'player'));model.update(1.)
        model.combatant('mira').hp = 0
        self.ready();self.assertTrue(model.choose_item('revival_salts', 'mira'));model.update(1.)
        record = self.victory()
        self.assertEqual(record['version'], 4)
        self.assertEqual(record['item_costs'], {'potion': 1, 'ether': 1, 'revival_salts': 1})
        before = deepcopy(game.inventory.to_dict())
        expected = encounter_drops('cave', ticket, ticket['receipt'], {})
        self.assertEqual(record['offered_drops'], expected)
        # Continue from the unawarded victory must preserve both the offer and costs.
        self.game = self.load();game = self.game
        wait_for_spoils(game)
        for item in ('potion', 'ether', 'revival_salts', 'rest_kit'):
            self.assertEqual(game.inventory.quantity(item), before['items'][item]
                             -record['item_costs'].get(item, 0)+expected.get(item, 0))
        self.assertTrue(valid_pending_snapshot(game.combat.snapshot(), json.loads(self.path.read_text())))
        inventory = game.inventory.to_dict();game.save_progress()
        self.game = self.load()
        self.assertEqual(self.game.inventory.to_dict(), inventory)
        self.assertEqual(self.game.combat.snapshot()['offered_drops'], expected)
        self.assertGreater(self.game.party.characters['mira'].current_hp, 0)

    def test_failed_award_rolls_back_consumption_loot_and_receipt_then_retries_once(self):
        self.cave();game = self.game;model = game.combat.model
        self.ready();model.choose_item('potion', 'player');model.update(1.)
        record = self.victory();before = game.inventory.to_dict()
        with patch.object(game.combat, '_apply_resources', return_value=False):
            spoils = wait_for_spoils(game)
        self.assertFalse(spoils.awarded)
        self.assertEqual(game.inventory.to_dict(), before)
        self.assertFalse(game.battle_rewards.has_receipt(record['receipt']))
        spoils.retry_requested = True;game.update(0, (0, 0), False)
        self.assertTrue(spoils.awarded)
        self.assertEqual(game.inventory.quantity('potion'), 4+record['offered_drops'].get('potion', 0))

    def test_used_item_opens_capacity_for_loot(self):
        self.cave(potion_full=True);model = self.game.combat.model
        self.ready();model.choose_item('potion', 'player');model.update(1.)
        record = self.victory();self.assertEqual(record['rewards']['drops'].get('potion'), 1)
        wait_for_spoils(self.game)
        self.assertEqual(self.game.inventory.quantity('potion'), MAX_QUANTITY)

    def test_defeat_restores_entry_resources_and_supplies_without_loot(self):
        self.cave();game = self.game;model = game.combat.model
        self.ready();model.choose_item('potion', 'player');model.update(1.)
        before = game.inventory.to_dict()
        for member in model.party:member.hp = 0
        model._result('defeat');game.combat.scene.dismissed = True
        game.update(0, (0, 0), False)
        self.assertFalse(game.combat.active)
        self.assertEqual(game.attributes.current_hp, 40)
        self.assertEqual(game.inventory.to_dict(), before)

    def test_failed_flee_checkpoint_keeps_costs_and_resources_available_for_one_retry(self):
        self.cave();game = self.game;model = game.combat.model
        self.ready();model.choose_item('potion', 'player');model.update(1.)
        self.ready();model.choose_item('smoke_bomb');model.update(1.)
        before = game.inventory.to_dict()
        game.combat.scene.dismissed = True
        with patch.object(game.save_store, 'write', return_value=False):game.update(0, (0, 0), False)
        self.assertTrue(game.combat.active)
        self.assertEqual(game.inventory.to_dict(), before)
        self.assertEqual(game.attributes.current_hp, 40)
        game.combat.scene.dismissed = True;game.update(0, (0, 0), False)
        self.assertFalse(game.combat.active)
        self.assertEqual(game.inventory.quantity('potion'), 4)
        self.assertEqual(game.inventory.quantity('smoke_bomb'), 2)
        self.assertEqual(game.attributes.current_hp, 140)

    def test_legacy_guaranteed_only_spoils_resume_without_adding_new_random_loot(self):
        ticket = self.cave();record = self.victory()
        data = json.loads(self.path.read_text())
        old = data['post_battle'];old['version'] = 2
        for key in ('rig_before', 'rig_after', 'rig_skill_uses', 'rig_healing', 'rig_stats'):old.pop(key)
        old.pop('item_costs');old.pop('item_before')
        old['offered_drops'] = battle_reward_definition('cave', ticket)['drops']
        old['rewards'] = {'drops': dict(old['offered_drops'])}
        self.path.write_text(json.dumps(data))
        before = self.game.inventory.to_dict()
        self.game = self.load();wait_for_spoils(self.game)
        self.assertEqual(self.game.inventory.to_dict(), before)
        self.assertEqual(self.game.combat.snapshot()['version'], 2)


if __name__ == '__main__':unittest.main()
