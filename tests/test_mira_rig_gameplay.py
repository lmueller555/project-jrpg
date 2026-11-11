"""Mira's live rig controls, restorative skills and durable battle transactions."""
from copy import deepcopy
import json
import os
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

import test_item_gameplay as item_helpers
from post_battle import (FIELDS, PARTY_FIELDS, PROGRESSION_FIELDS, ITEM_FIELDS,
                         battle_reward_definition, valid_pending_snapshot)
from test_mill_battle_gameplay import key, click, wait_for_spoils

DEFAULT = {'weapons': 2, 'protection': 2, 'support': 2}
SUPPORT = {'weapons': 0, 'protection': 3, 'support': 3}
OFFENSE = {'weapons': 3, 'protection': 1, 'support': 2}


class RigGameFixture(unittest.TestCase):
    """Use established real-Game entry helpers without inheriting item tests."""
    setUp = item_helpers.ItemGameplayTests.setUp
    load = item_helpers.ItemGameplayTests.load
    ready = item_helpers.ItemGameplayTests.ready
    click_command = item_helpers.ItemGameplayTests.click_command
    cave = item_helpers.ItemGameplayTests.cave
    victory = item_helpers.ItemGameplayTests.victory

    def configure(self, allocation):
        self.ready('mira')
        self.assertTrue(self.game.combat.model.set_rig_allocation(allocation))
        self.game.draw()

    def skill(self, identifier, target=None):
        self.ready('mira')
        model = self.game.combat.model
        self.assertTrue(model.choose_action(identifier, actor_id='mira', target_id=target),
                        model.action_reason(identifier, 'mira'))
        duration = model.current_action.duration
        model.update(duration)
        self.assertIsNone(model.current_action)

    def settle_flee(self):
        model = self.game.combat.model
        self.ready('mira')
        self.assertTrue(model.choose_action('flee', actor_id='mira'))
        model.update(model.current_action.duration)
        self.assertEqual(model.phase, 'fled')
        self.game.combat.scene.dismissed = True
        self.game.update(0, (0, 0), False)

    def finish_entry(self):
        for _ in range(150):
            self.game.update(.05, (0, 0), False);self.game.draw()
            if self.game.combat.model is not None and not self.game.combat.transitioning:return
        self.fail('Continued cave encounter did not finish its production entry')


class MiraRigGameplayTests(RigGameFixture):
    def test_unfinished_continue_restarts_entry_allocation_without_bot_or_resource_grant(self):
        entry = {'weapons': 3, 'protection': 3, 'support': 0}
        self.assertTrue(self.game.mira_rig.set_allocation(entry))
        self.cave()
        self.assertEqual(self.game.combat.model.rig_allocation, entry)
        self.assertEqual(self.game.combat.model.bots, ())
        self.configure(SUPPORT)
        self.skill('repair_pulse', 'player')
        self.assertGreater(self.game.combat.model.player.hp, self.game.attributes.current_hp)
        self.assertTrue(self.game.save_progress())
        self.assertEqual(self.game.mira_rig.allocation, entry)
        self.game = self.load();self.finish_entry()
        self.assertEqual(self.game.mira_rig.allocation, entry)
        self.assertEqual(self.game.combat.model.rig_allocation, entry)
        self.assertEqual(self.game.combat.model.player.hp, 40)
        self.assertEqual(self.game.combat.model.combatant('mira').mp, 30)
        self.assertEqual(self.game.combat.model.bots, ())

    def test_repair_menu_cancel_and_click_ally_use_real_mira_turn_and_mp(self):
        self.cave();self.configure(SUPPORT)
        model = self.game.combat.model
        before = (model.player.hp, model.combatant('mira').mp)
        self.click_command('skills');self.click_command('repair_pulse')
        self.assertEqual(self.game.combat.scene.command_menu, 'skill_targets')
        key(self.game, pygame.K_ESCAPE)
        self.assertEqual((model.player.hp, model.combatant('mira').mp), before)
        self.click_command('repair_pulse');self.game.draw()
        click(self.game, self.game.combat.scene.party_rows['player']['row'].center)
        self.assertEqual(model.current_action.action, 'repair_pulse')
        self.assertEqual(model.combatant('mira').mp, before[1]-4)
        model.update(model.current_action.duration)
        self.assertGreater(model.player.hp, before[0])
        self.assertEqual(self.game.attributes.current_hp, 40)
        self.assertEqual(model.combatant('mira').atb, 0.)

    def test_healed_victory_resumes_pending_and_awarded_once_with_configuration(self):
        self.cave();self.configure(SUPPORT)
        self.skill('repair_pulse', 'player')
        healed = self.game.combat.model.player.hp
        self.assertGreater(healed, 40)
        record = self.victory()
        self.assertEqual(record['version'], 4)
        self.assertEqual(record['rig_before']['allocation'], DEFAULT)
        self.assertEqual(record['rig_after']['allocation'], SUPPORT)
        self.assertEqual(record['rig_skill_uses'], {'repair_pulse': 1})
        self.assertEqual(record['rig_healing'], {'caelan': healed-40})
        self.assertEqual(self.game.mira_rig.allocation, DEFAULT)
        self.game = self.load();spoils = wait_for_spoils(self.game)
        self.assertTrue(spoils.awarded)
        self.assertEqual(self.game.attributes.current_hp, healed)
        self.assertEqual(self.game.party.characters['mira'].current_mp, 26)
        self.assertEqual(self.game.mira_rig.allocation, SUPPORT)
        awarded = deepcopy(self.game.inventory.to_dict())
        levels = deepcopy(self.game.character_progression.to_dict())
        self.assertTrue(self.game.save_progress())
        self.game = self.load()
        self.assertEqual(self.game.inventory.to_dict(), awarded)
        self.assertEqual(self.game.character_progression.to_dict(), levels)
        self.assertEqual(self.game.mira_rig.allocation, SUPPORT)
        self.assertTrue(valid_pending_snapshot(self.game.combat.snapshot(),
                                              json.loads(self.path.read_text())))

    def test_ether_then_repair_settles_consumption_restoration_and_skill_expenditure(self):
        self.assertTrue(self.game.party.characters['mira'].set_current(mp=0))
        self.cave();self.configure(SUPPORT)
        model = self.game.combat.model
        self.ready('player')
        self.assertTrue(model.choose_item('ether', 'mira'))
        model.update(model.current_action.duration)
        self.assertEqual(model.combatant('mira').mp, 15)
        self.skill('repair_pulse', 'player')
        self.assertEqual(model.combatant('mira').mp, 11)
        record = self.victory()
        self.assertEqual(record['item_costs'], {'ether': 1})
        self.assertEqual(record['rig_skill_uses'], {'repair_pulse': 1})
        self.game = self.load();self.assertTrue(wait_for_spoils(self.game).awarded)
        self.assertEqual(self.game.party.characters['mira'].current_mp, 11)
        self.assertEqual(self.game.inventory.quantity('ether'),
                         4+record['rewards']['drops'].get('ether', 0))
        self.assertEqual(self.game.mira_rig.allocation, SUPPORT)

    def test_failed_award_restores_allocation_then_retry_grants_once(self):
        self.cave();self.configure(SUPPORT);self.skill('repair_pulse', 'player')
        record = self.victory();before = self.game.inventory.to_dict()
        with patch.object(self.game.combat, '_apply_resources', return_value=False):
            spoils = wait_for_spoils(self.game)
        self.assertFalse(spoils.awarded)
        self.assertEqual(self.game.mira_rig.allocation, DEFAULT)
        self.assertEqual(self.game.inventory.to_dict(), before)
        self.assertFalse(self.game.battle_rewards.has_receipt(record['receipt']))
        spoils.retry_requested = True;self.game.update(0, (0, 0), False)
        self.assertTrue(spoils.awarded)
        self.assertEqual(self.game.mira_rig.allocation, SUPPORT)
        self.assertTrue(self.game.battle_rewards.has_receipt(record['receipt']))

    def test_failed_flee_rolls_back_allocation_resources_then_commits_one_retry(self):
        self.cave();self.configure(SUPPORT);self.skill('repair_pulse', 'player')
        model = self.game.combat.model
        healed = model.player.hp
        self.ready('mira');self.assertTrue(model.choose_action('flee', actor_id='mira'))
        model.update(model.current_action.duration)
        self.game.combat.scene.dismissed = True
        with patch.object(self.game.save_store, 'write', return_value=False):
            self.game.update(0, (0, 0), False)
        self.assertTrue(self.game.combat.active)
        self.assertEqual(self.game.mira_rig.allocation, DEFAULT)
        self.assertEqual(self.game.attributes.current_hp, 40)
        self.game.combat.scene.dismissed = True;self.game.update(0, (0, 0), False)
        self.assertFalse(self.game.combat.active)
        self.assertEqual(self.game.mira_rig.allocation, SUPPORT)
        self.assertEqual(self.game.attributes.current_hp, healed)
        self.assertEqual(self.load().mira_rig.allocation, SUPPORT)

    def test_defeat_keeps_entry_allocation_resources_and_supplies(self):
        self.cave();self.configure(SUPPORT);self.skill('repair_pulse', 'player')
        before = self.game.inventory.to_dict()
        model = self.game.combat.model
        for member in model.party:member.hp = 0
        model._result('defeat');self.game.combat.scene.dismissed = True
        self.game.update(0, (0, 0), False)
        self.assertFalse(self.game.combat.active)
        self.assertEqual(self.game.mira_rig.allocation, DEFAULT)
        self.assertEqual(self.game.attributes.current_hp, 40)
        self.assertEqual(self.game.inventory.to_dict(), before)

    def test_v4_rejects_forged_healing_costs_and_allocations(self):
        self.cave();self.configure(SUPPORT);self.skill('repair_pulse', 'player')
        record = self.victory()
        for field, value in (
                ('rig_healing', {'caelan': 9999}),
                ('rig_skill_uses', {'repair_pulse': 8}),
                ('rig_skill_uses', {'unregistered_repair': 1}),
                ('rig_skill_uses', {}),
                ('rig_after', {'version': 1, 'allocation': {'weapons': 7, 'protection': 0, 'support': 0}})):
            with self.subTest(field=field, value=value):
                forged = deepcopy(record);forged[field] = value
                self.assertFalse(valid_pending_snapshot(forged))

    def test_effective_spirit_modifier_healing_preserves_its_entry_basis_on_continue(self):
        self.assertTrue(self.game.party.characters['mira'].set_modifiers('entry_calibration', {'spr': 10}))
        self.cave();self.configure(SUPPORT);self.skill('repair_pulse', 'player')
        self.assertEqual(self.game.combat.model.player.hp, 101)
        record = self.victory()
        self.assertEqual(record['rig_stats']['mira']['spr'], 20)
        for invalid in (True, 1000, 9):
            forged = deepcopy(record);forged['rig_stats']['mira']['spr'] = invalid
            self.assertFalse(valid_pending_snapshot(forged))
        self.game = self.load();self.assertTrue(wait_for_spoils(self.game).awarded)
        self.assertEqual(self.game.attributes.current_hp, 101)
        self.assertEqual(self.game.party.characters['mira'].current_mp, 26)

    def test_v1_v2_v3_pending_victories_keep_their_original_resource_and_loot_rules(self):
        ticket = self.cave();self.victory()
        modern = json.loads(self.path.read_text())
        inventory = self.game.inventory.to_dict()
        for version in (1, 2, 3):
            with self.subTest(version=version):
                data = deepcopy(modern);record = data['post_battle']
                keep = FIELDS | PARTY_FIELDS | {'encounter'}
                if version >= 2:keep |= PROGRESSION_FIELDS
                if version >= 3:keep |= ITEM_FIELDS
                record = {key: value for key, value in record.items() if key in keep}
                record['version'] = version
                if version < 3:
                    drops = battle_reward_definition('cave', ticket)['drops']
                    record['rewards'] = {'drops': drops}
                    if version == 2:record['offered_drops'] = drops
                data['post_battle'] = record
                self.assertTrue(valid_pending_snapshot(record, data))
                self.path.write_text(json.dumps(data))
                self.game = self.load();self.assertTrue(wait_for_spoils(self.game).awarded)
                self.assertEqual(self.game.combat.snapshot()['version'], version)
                self.assertEqual(self.game.mira_rig.allocation, DEFAULT)
                if version < 3:self.assertEqual(self.game.inventory.to_dict(), inventory)


if __name__ == '__main__':unittest.main()
