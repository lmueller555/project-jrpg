"""Real victories persist EXP, stat growth and item receipts together once."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from cave_random_encounters import CaveRandomEncounters
from inventory import MAX_QUANTITY
from leveling import CharacterLevel, MAX_TOTAL_XP
from main import Game
from post_battle import battle_reward_definition, valid_pending_snapshot
from test_mill_battle_gameplay import seed_completed_mill, wait_for_spoils


class BattleExperienceTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='battle-exp-')
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.path = self.directory/'journey.json'
        self.game = self.new_game()
        seed_completed_mill(self.game)

    def tearDown(self):pygame.quit()

    def new_game(self, title=False):
        game = Game(window_size=(960, 640), fullscreen=False, start_on_title=title,
                    save_path=self.path, settings_path=self.directory/'settings.json')
        game.audio.set_music(0);game.audio.set_effects(0)
        game.opening_fade = game.transfer_cooldown = 0
        pygame.event.clear()
        return game

    def start(self):
        game = self.game
        game.player.position.update(game.combat.position+(0, 24))
        game.player.facing = 'back';game.camera.reset()
        self.assertTrue(game.combat.interact())
        game.combat.transition = None
        return game.combat

    def victory(self, owner=None):
        owner = owner or self.start()
        for enemy in owner.model.enemies:enemy.hp = 0
        owner.model._result('victory')
        self.assertTrue(owner._begin_victory())
        return owner

    def show_spoils(self):return wait_for_spoils(self.game)

    def total(self, identifier='caelan', game=None):
        return (game or self.game).character_progression[identifier].total_xp

    def persisted(self):return json.loads(self.path.read_text())

    def load(self):
        game = self.new_game(title=True)
        self.assertTrue(game.has_saved_journey, game.save_error)
        self.assertTrue(game.begin_journey(True), game.save_error)
        return game

    def test_continue_finishes_a_pre_rebalance_pending_reward_at_its_original_amount(self):
        owner = self.victory()
        data = self.persisted()
        plan = owner.snapshot()['progression']
        data['post_battle']['progression'] = self.game.character_progression.preview(
            60, plan['active_ids'], plan['end_hp'])
        self.path.write_text(json.dumps(data))
        restored = self.load()
        wait_for_spoils(restored)
        self.assertEqual(self.total(game=restored), 60)
        self.assertEqual(restored.combat.snapshot()['progression']['amount'], 60)

    def previous_curve_spoils(self, *, awarded):
        with patch('post_battle.monster_xp', return_value=42):
            owner = self.victory()
            if awarded:self.show_spoils()
        self.assertEqual(owner.snapshot()['progression']['amount'], 42)
        restored = self.load()
        wait_for_spoils(restored)
        self.assertEqual(self.total(game=restored), 42)
        self.assertTrue(valid_pending_snapshot(restored.combat.snapshot(), self.persisted()))
        restored.save_progress()
        again = self.load()
        self.assertEqual(self.total(game=again), 42)

    def test_previous_curve_pending_spoils_keep_original_exp_on_continue(self):
        self.previous_curve_spoils(awarded=False)

    def test_previous_curve_awarded_spoils_do_not_regrant_exp_on_continue(self):
        self.previous_curve_spoils(awarded=True)

    def test_survivors_each_receive_full_exp_and_ko_before_first_aid_gets_none(self):
        game = self.game
        for identifier in ('mira', 'lucan', 'rhea'):
            if identifier not in game.party.members:self.assertTrue(game.party.recruit(identifier))
        self.assertTrue(game.party.set_available('mira', True))
        self.assertTrue(game.party.select(('caelan', 'mira', 'lucan')))
        owner = self.start()
        owner.model.player.hp = 0
        owner.model.combatant('mira').hp = 83
        owner.model.combatant('lucan').hp = 67
        self.victory(owner)
        self.assertEqual(owner.snapshot()['progression']['end_hp']['caelan'], 0)
        self.assertGreater(owner.snapshot()['resources']['hp'], 0)
        self.show_spoils()
        self.assertEqual([self.total(key) for key in ('caelan', 'mira', 'lucan', 'rhea')],
                         [0, 24, 24, 0])
        self.assertEqual(game.party.characters['mira'].current_hp, 83)
        self.assertEqual(game.party.characters['lucan'].current_hp, 67)
        self.assertTrue(valid_pending_snapshot(owner.snapshot(), self.persisted()))

    def test_level_up_adds_growth_without_healing_and_saves_both_before_and_after(self):
        game = self.game
        game.character_progression.records['caelan'] = CharacterLevel('caelan', 190)
        owner = self.start()
        owner.model.player.hp, owner.model.player.mp = 47, 7
        self.victory(owner)
        plan = owner.snapshot()['progression']['characters']['caelan']
        self.assertEqual((plan['old_level'], plan['new_level']), (1, 2))
        self.assertEqual(self.total(), 190)
        self.assertEqual(self.persisted()['character_levels']['characters']['caelan']['total_xp'], 190)
        self.show_spoils()
        self.assertEqual(self.total(), 214)
        self.assertEqual(game.character_progression.level('caelan'), 2)
        self.assertEqual((game.attributes.current_hp, game.attributes.current_mp), (47, 7))
        self.assertEqual(game.attributes.to_dict()['attributes'], plan['stats_after'])
        self.assertTrue(valid_pending_snapshot(owner.snapshot(), self.persisted()))

    def test_failed_award_write_retries_checkpoint_without_second_exp_or_stat_grant(self):
        game = self.game
        game.character_progression.records['caelan'] = CharacterLevel('caelan', 190)
        owner = self.victory()
        with patch.object(game.save_store, 'write', return_value=False):
            spoils = self.show_spoils()
        self.assertEqual(owner.snapshot()['stage'], 'awarded')
        self.assertFalse(spoils.ready)
        self.assertEqual(self.total(), 214)
        after = game.attributes.to_dict()
        self.assertEqual(self.persisted()['post_battle']['stage'], 'pending')
        with patch.object(game.character_progression, 'apply', side_effect=AssertionError('duplicate EXP')):
            spoils.retry_requested = True;game.update(0, (0, 0), False)
        self.assertTrue(spoils.ready)
        self.assertEqual(self.total(), 214)
        self.assertEqual(game.attributes.to_dict(), after)
        self.assertTrue(valid_pending_snapshot(owner.snapshot(), self.persisted()))

    def test_initial_checkpoint_failure_grants_neither_exp_nor_items_until_retry(self):
        game = self.game
        with patch.object(game.save_store, 'write', return_value=False):
            owner = self.victory();spoils = self.show_spoils()
        self.assertFalse(spoils.ready)
        self.assertEqual(self.total(), 0)
        self.assertEqual(game.inventory.quantity('aether_emerald'), 0)
        self.assertFalse(game.battle_rewards.has_receipt(owner.receipt_id))
        spoils.retry_requested = True;game.update(0, (0, 0), False)
        self.assertTrue(spoils.ready)
        self.assertEqual(self.total(), 24)
        self.assertEqual(game.inventory.quantity('aether_emerald'), 1)

    def test_late_transaction_failure_rolls_back_items_receipt_exp_and_growth(self):
        game = self.game
        game.character_progression.records['caelan'] = CharacterLevel('caelan', 190)
        owner = self.victory()
        before = game.attributes.to_dict()
        with patch.object(owner, '_apply_resources', return_value=False):
            spoils = self.show_spoils()
        self.assertFalse(spoils.ready)
        self.assertEqual(owner.snapshot()['stage'], 'pending')
        self.assertEqual(self.total(), 190)
        self.assertEqual(game.attributes.to_dict(), before)
        self.assertEqual(game.inventory.quantity('aether_emerald'), 0)
        self.assertFalse(game.battle_rewards.has_receipt(owner.receipt_id))
        spoils.retry_requested = True;game.update(0, (0, 0), False)
        self.assertTrue(spoils.ready)
        self.assertEqual(self.total(), 214)

    def test_continue_pending_or_awarded_victory_does_not_repeat_exp_or_growth(self):
        game = self.game
        game.character_progression.records['caelan'] = CharacterLevel('caelan', 190)
        owner = self.victory()
        original = owner.snapshot()['progression']
        restored = self.load()
        self.assertEqual(restored.character_progression['caelan'].total_xp, 214)
        self.assertEqual(restored.combat.snapshot()['progression'], original)
        after = restored.attributes.to_dict()
        restored.save_progress()
        again = self.load()
        self.assertEqual(again.character_progression['caelan'].total_xp, 214)
        self.assertEqual(again.attributes.to_dict(), after)
        self.assertEqual(len(again.battle_rewards.to_dict()['receipts']), 1)
        self.assertTrue(valid_pending_snapshot(again.combat.snapshot(), self.persisted()))

    def test_forged_amount_eligibility_growth_before_or_saved_xp_are_rejected(self):
        game = self.game
        game.character_progression.records['caelan'] = CharacterLevel('caelan', 190)
        owner = self.victory();data = self.persisted()
        for mutate in (
            lambda r:r['progression'].update(amount=6000),
            lambda r:r['progression']['end_hp'].update(caelan=0),
            lambda r:r['progression']['characters']['caelan']['stat_gains'].update(hp=900),
            lambda r:r['progression']['characters']['caelan']['stats_before'].update(hp=999),
            lambda r:r['progression']['characters']['caelan'].update(old_total_xp=True),
            lambda r:r['offered_drops'].update(aether_emerald=True),
        ):
            record = owner.snapshot();mutate(record)
            self.assertFalse(valid_pending_snapshot(record, data), record)
        bad = deepcopy(data);bad['character_levels']['characters']['caelan']['total_xp'] += 1
        self.assertFalse(valid_pending_snapshot(owner.snapshot(), bad))
        self.show_spoils()
        bad = self.persisted();bad['party']['characters']['caelan']['attributes']['str'] += 1
        bad['character_attributes']['attributes']['str'] += 1
        self.assertFalse(valid_pending_snapshot(owner.snapshot(), bad))

    def test_old_pending_victory_remains_readable_without_retroactive_exp(self):
        self.victory()
        data = self.persisted()
        data['post_battle']['version'] = 1
        data['post_battle'].pop('item_costs');data['post_battle'].pop('item_before')
        data['post_battle'].pop('progression');data['post_battle'].pop('offered_drops')
        data.pop('character_levels')
        self.path.write_text(json.dumps(data))
        restored = self.load()
        self.assertEqual(restored.character_progression['caelan'].total_xp, 0)
        self.assertEqual(restored.inventory.quantity('aether_emerald'), 1)
        self.assertEqual(restored.combat.snapshot()['version'], 1)

    def test_flee_and_defeat_award_no_exp_or_items(self):
        for outcome in ('fled', 'defeat'):
            with self.subTest(outcome=outcome):
                owner = self.start()
                owner.model.enemy.hp = 0
                owner.model._result(outcome)
                owner.scene.dismissed = True
                self.game.update(0, (0, 0), False)
                self.assertFalse(owner.active)
                self.assertEqual(self.total(), 0)
                self.assertEqual(self.game.inventory.quantity('aether_emerald'), 0)
                owner.cooldown = 0

    def test_level_cap_discards_overflow_and_still_grants_the_item(self):
        game = self.game
        game.character_progression.records['caelan'] = CharacterLevel('caelan', MAX_TOTAL_XP-10)
        owner = self.victory();self.show_spoils()
        plan = owner.snapshot()['progression']['characters']['caelan']
        self.assertEqual((plan['accepted_xp'], plan['discarded_xp']), (10, 14))
        self.assertEqual(self.total(), MAX_TOTAL_XP)
        self.assertEqual(game.character_progression.level('caelan'), 100)
        self.assertEqual(game.inventory.quantity('aether_emerald'), 1)
        self.assertTrue(valid_pending_snapshot(owner.snapshot(), self.persisted()))

    def test_full_inventory_still_awards_exp_and_retains_offered_item_metadata(self):
        game = self.game
        self.assertTrue(game.inventory.add_many({'aether_emerald': MAX_QUANTITY}))
        owner = self.victory();self.show_spoils()
        self.assertEqual(owner.snapshot()['rewards'], {'drops': {}})
        self.assertEqual(owner.snapshot()['offered_drops'], {'aether_emerald': 1})
        self.assertEqual(self.total(), 24)
        self.assertEqual(game.inventory.quantity('aether_emerald'), MAX_QUANTITY)
        self.assertTrue(valid_pending_snapshot(owner.snapshot(), self.persisted()))

    def test_cave_group_uses_sum_of_reduced_monster_exp(self):
        game = self.game
        game.character_progression.records['caelan'] = CharacterLevel('caelan', 190)
        for seed in range(1000):
            controller = CaveRandomEncounters(seed)
            ticket = controller.advance(1000, (1680, 970))
            if ticket is not None and len(ticket['members']) == 4:break
        else:self.fail('Deep encounter pool did not produce a group of four')
        self.assertTrue(game.cave_random_encounters.restore(controller.to_dict()))
        game.world = game._scene_by_id('sanctuary_cave')
        game.player.position.update(ticket['position']);game.camera.reset()
        self.assertTrue(game.combat.start_cave(ticket))
        for _ in range(60):
            if game.combat.model is not None:break
            game.update(.1, (0, 0), False);game.draw()
        self.assertIsNotNone(game.combat.model)
        game.combat.transition = None
        owner = self.victory(game.combat);self.show_spoils()
        amount = battle_reward_definition('cave', ticket)['xp']
        self.assertEqual(self.total(), 190+amount)
        self.assertGreaterEqual(game.character_progression.level('caelan'), 2)
        self.assertEqual(owner.snapshot()['progression']['amount'], amount)
        self.assertTrue(valid_pending_snapshot(owner.snapshot(), self.persisted()))


if __name__ == '__main__':unittest.main()
