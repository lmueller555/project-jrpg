"""Shared consumable effects, independent loot rolls and durable starter supplies."""
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

from bestiary import build_enemy, load_bestiary
from battle_model import BattleModel
from character_attributes import CharacterAttributes
from consumables import field_reason, use_field_item
from enemy_loot import encounter_drops, roll_table
from inventory import Inventory

START = {'potion': 5, 'ether': 5, 'revival_salts': 3, 'smoke_bomb': 3, 'rest_kit': 3}
CAVE = {'cave_bat': 2, 'lithrusk': 2, 'veylume': 3,
        'embravyr': 4, 'nivareth': 4, 'vespermaw': 7}
TABLE = [{'item': key, 'chance': rate, 'quantity': 1}
         for key, rate in [('potion', 15), ('revival_salts', 10), ('ether', 5), ('rest_kit', 5)]]


class ConsumableModelTests(unittest.TestCase):
    def model(self, boss=False):
        model = (BattleModel.from_bestiary(CharacterAttributes(), 'vespermaw', 7, guest_id='mira')
                 if boss else BattleModel(CharacterAttributes(), guest_id='mira', rng=random.Random(5)))
        model.set_item_inventory(Inventory.new_journey())
        return model

    def ready(self, model, actor='player'):
        model.phase = 'charging';model.current_action = None
        for member in (*model.party, *model.enemies):member.atb = 0.
        model.combatant(actor).atb = 1.;model.update(0)
        self.assertEqual(model.ready_actor, actor)

    def test_healing_and_mp_apply_at_impact_clamp_and_spend_one_turn_without_mp(self):
        model = self.model();model.player.hp = 20;model.player.mp = 0
        self.ready(model)
        self.assertTrue(model.choose_item('potion', 'player'))
        self.assertEqual((model.player.atb, model.player.mp, model.item_counts['potion']), (0, 0, 4))
        model.update(.49);self.assertEqual(model.player.hp, 20)
        model.update(.01);self.assertEqual(model.player.hp, 120)
        self.ready(model);self.assertTrue(model.choose_item('potion', 'player'));model.update(.5)
        self.assertEqual(model.player.hp, 140)
        self.ready(model);self.assertFalse(model.choose_item('potion', 'player'))
        self.assertEqual(model.item_counts['potion'], 3)
        model.player.mp = 25
        self.assertTrue(model.choose_item('ether', 'player'));model.update(.5)
        self.assertEqual(model.player.mp, 30)
        self.assertEqual(model.item_spent, {'potion': 2, 'ether': 1})

    def test_revival_can_target_only_ko_party_without_free_atb_or_autonomous_actor(self):
        model = self.model();mira = model.combatant('mira')
        mira.hp = 0;model._sync_party_activity()
        self.ready(model)
        before = dict(model.item_counts)
        for item, target in [('potion', 'mira'), ('ether', 'mira'),
                             ('revival_salts', 'player'), ('revival_salts', 'enemy'),
                             ('rest_kit', 'player')]:
            self.assertFalse(model.choose_item(item, target))
        self.assertEqual(model.item_counts, before)
        self.assertTrue(model.choose_item('revival_salts', 'mira'));model.update(.5)
        self.assertEqual(mira.hp, 38)
        self.assertEqual(mira.atb, 0.)
        self.assertFalse(hasattr(model, 'active_bot'))
        self.assertFalse(any(event['type'] == 'bot_resumed' for event in model.drain_events()))

    def test_smoke_obeys_flee_rules_and_no_items_can_skip_a_guided_lesson(self):
        model = self.model();self.ready(model)
        self.assertTrue(model.choose_item('smoke_bomb'));model.update(1.)
        self.assertEqual(model.phase, 'fled')
        self.assertEqual(model.item_spent, {'smoke_bomb': 1})
        boss = self.model(True);self.ready(boss)
        self.assertFalse(boss.choose_item('smoke_bomb'))
        self.assertEqual(boss.item_counts['smoke_bomb'], 3)
        lesson = BattleModel(CharacterAttributes(), enemy_id='ridgeback_tusker',
                             guest_id='mira', weapon_equipped=True, spellblade_tutorial=True)
        lesson.set_item_inventory(Inventory.new_journey());self.ready(lesson)
        lesson.player.hp = 10
        self.assertFalse(lesson.choose_item('potion', 'player'))
        self.assertFalse(lesson.choose_item('smoke_bomb'))
        self.assertEqual(lesson.item_spent, {})

    def test_another_ready_character_can_use_the_same_shared_inventory(self):
        model = self.model();model.player.hp = 1;self.ready(model, 'mira')
        self.assertTrue(model.choose_item('potion', 'player'))
        self.assertEqual(model.current_action.actor, 'mira')
        model.update(.5);self.assertEqual(model.player.hp, 101)


class CaveDropTableTests(unittest.TestCase):
    def test_all_six_cave_enemies_have_the_requested_shared_independent_rates(self):
        for identifier, level in CAVE.items():
            with self.subTest(enemy=identifier):
                record = build_enemy(identifier, level)
                self.assertEqual(record['metadata']['rewards']['drop_table'], TABLE)
                self.assertFalse(record['metadata']['drops_pending'])
        self.assertNotIn('drop_table', build_enemy('ridgeback_tusker', 1)['metadata']['rewards'])

    def test_each_roll_boundary_and_multiple_items_from_one_enemy(self):
        rng = unittest.mock.Mock()
        rng.randrange.side_effect = [14, 9, 4, 4]
        self.assertEqual(roll_table(TABLE, rng), {'potion': 1, 'revival_salts': 1, 'ether': 1, 'rest_kit': 1})
        rng.randrange.side_effect = [15, 10, 5, 5]
        self.assertEqual(roll_table(TABLE, rng), {})

    def test_formation_rolls_per_enemy_and_saved_identity_repeats_exactly(self):
        ticket = {'members': [{'enemy_id': 'cave_bat', 'level': 2}]*4, 'combat_seed': 19}
        with patch('enemy_loot.random.Random') as rng:
            rng.return_value.randrange.return_value = 0
            self.assertEqual(encounter_drops('cave', ticket, 'cave:test', {}),
                             {'potion': 4, 'revival_salts': 4, 'ether': 4, 'rest_kit': 4})
            self.assertEqual(rng.return_value.randrange.call_count, 16)
        first = encounter_drops('cave', ticket, 'cave:test', {})
        self.assertEqual(first, encounter_drops('cave', ticket, 'cave:test', {}))
        self.assertGreater(len({json.dumps(encounter_drops('cave', {**ticket, 'combat_seed': seed},
            'cave:test', {}), sort_keys=True) for seed in range(20)}), 1)

    def test_invalid_drop_rows_are_rejected_without_mutating_the_dictionary(self):
        original = load_bestiary()
        for row in ({'item': 'potion', 'chance': True, 'quantity': 1},
                    {'item': 'potion', 'chance': 101, 'quantity': 1},
                    {'item': 'missing', 'chance': 5, 'quantity': 1},
                    {'item': 'halden_medicine', 'chance': 5, 'quantity': 1},
                    {'item': 'potion', 'chance': 5, 'quantity': 0}):
            data = deepcopy(original)
            data['enemies']['cave_bat']['rewards']['drop_table'] = [row]
            with self.assertRaises(ValueError):load_bestiary(data)
        data = deepcopy(original)
        data['enemies']['cave_bat']['rewards']['drop_table'] = [TABLE[0], TABLE[0]]
        with self.assertRaises(ValueError):load_bestiary(data)


class ConsumableFieldTests(unittest.TestCase):
    def setUp(self):
        from main import Game
        from test_mill_battle_gameplay import seed_completed_mill
        self.folder = tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name)/'journey.json'
        self.settings = Path(self.folder.name)/'settings.json'
        self.game = Game(fullscreen=False, start_on_title=False,
                         save_path=self.path, settings_path=self.settings)
        self.game.audio.set_music(0);self.game.audio.set_effects(0)
        self.addCleanup(pygame.quit)
        seed_completed_mill(self.game)
        if 'mira' not in self.game.party.members:self.game.party.recruit('mira')
        self.game.party.set_available('mira', True)

    def test_starting_supplies_once_and_continue_never_refills_them(self):
        from main import Game
        self.assertEqual({key: self.game.inventory.quantity(key) for key in START}, START)
        self.game.attributes.set_current(hp=10)
        self.assertTrue(use_field_item(self.game, 'potion', 'caelan')[0])
        self.assertEqual(self.game.attributes.current_hp, 110)
        other = Game(fullscreen=False, start_on_title=True, save_path=self.path, settings_path=self.settings)
        self.assertTrue(other.begin_journey(True), other.save_error)
        self.assertEqual(other.inventory.quantity('potion'), 4)
        self.assertEqual(other.attributes.current_hp, 110)
        self.assertTrue(other.begin_journey(False, show_cinematic=False))
        self.assertEqual({key: other.inventory.quantity(key) for key in START}, START)

    def test_field_target_rules_restore_and_save_failure_roll_back_the_complete_use(self):
        game = self.game;mira = game.party.characters['mira']
        mira.set_current(hp=0, mp=0)
        before = game.inventory.to_dict()
        self.assertFalse(use_field_item(game, 'potion', 'mira')[0])
        self.assertFalse(use_field_item(game, 'revival_salts', 'caelan')[0])
        for key in ('smoke_bomb', 'rest_kit', 'halden_medicine'):
            self.assertTrue(field_reason(game, key, 'caelan'))
        self.assertEqual(game.inventory.to_dict(), before)
        with patch.object(game.save_store, 'write', return_value=False):
            self.assertFalse(use_field_item(game, 'revival_salts', 'mira')[0])
        self.assertEqual(mira.current_hp, 0)
        self.assertEqual(game.inventory.to_dict(), before)
        self.assertTrue(use_field_item(game, 'revival_salts', 'mira')[0])
        self.assertEqual(mira.current_hp, 38)
        self.assertTrue(use_field_item(game, 'ether', 'mira')[0])
        self.assertEqual(mira.current_mp, 15)


if __name__ == '__main__':unittest.main()
