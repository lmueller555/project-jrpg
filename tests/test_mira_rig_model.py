"""Deterministic wearable-rig actions, requirements and transient protection."""
from copy import deepcopy
import json
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from battle_model import BattleAction, BattleModel, load_actions
from character_attributes import CharacterAttributes
from combat_damage import magical_damage, physical_damage
from mira_rig_rules import SKILLS, barrier_amount, healing_amount


class MiraRigModelTests(unittest.TestCase):
    def model(self, **options):
        return BattleModel(CharacterAttributes(), guest_id='mira', rng=random.Random(5), **options)

    def ready(self, model, actor='mira'):
        model.phase = 'charging';model.current_action = None
        for member in (*model.party, *model.enemies):member.atb = 0.
        model.combatant(actor).atb = 1.;model.update(0)
        self.assertEqual(model.ready_actor, actor)

    def act(self, model, identifier, target=None):
        self.ready(model)
        self.assertTrue(model.choose_action(identifier, target_id=target), model.action_reason(identifier, target_id=target))
        model.update(model.current_action.duration)

    def test_default_configuration_known_skills_and_no_autonomous_actor(self):
        model = self.model()
        self.assertEqual(model.rig_allocation, dict(weapons=2, protection=2, support=2))
        self.assertEqual(model.skill_actions('mira'), list(SKILLS))
        self.assertFalse(hasattr(model, 'bots'))
        self.assertFalse(any(event['type'] == 'bot_deployed' for event in model.drain_events()))
        self.assertEqual(self.model(guest_abilities={'mira': []}).skill_actions('mira'), [])

    def test_configuration_validates_atomically_without_resources_or_turns(self):
        model = self.model()
        before = [(member.hp, member.mp, member.atb) for member in model.party]
        for bad in ({}, {'weapons': True, 'protection': 2, 'support': 3},
                    {'weapons': 7, 'protection': 0, 'support': -1},
                    {'weapons': 2, 'protection': 2, 'support': 1}):
            self.assertFalse(model.set_rig_allocation(bad))
        allocation = dict(weapons=3, protection=0, support=3)
        self.assertTrue(model.set_rig_allocation(allocation))
        allocation['weapons'] = 0
        exposed = model.rig_allocation;exposed['support'] = 0
        self.assertEqual(model.rig_allocation, dict(weapons=3, protection=0, support=3))
        self.assertEqual(before, [(member.hp, member.mp, member.atb) for member in model.party])
        self.ready(model, 'player')
        self.assertFalse(model.set_rig_allocation(dict(weapons=0, protection=3, support=3)))
        self.ready(model)
        self.assertTrue(model.set_rig_allocation(dict(weapons=0, protection=3, support=3)))

    def test_configuration_unavailable_for_absent_ko_guided_or_ended_mira(self):
        self.assertTrue(BattleModel(CharacterAttributes()).rig_reason())
        model = self.model();model.combatant('mira').hp = 0
        self.assertTrue(model.rig_reason())
        lesson = self.model(enemy_id='ridgeback_tusker', weapon_equipped=True, spellblade_tutorial=True)
        self.assertTrue(lesson.rig_reason())
        model = self.model();model._result('fled')
        self.assertTrue(model.rig_reason())

    def test_requirements_are_minimums_and_actor_specific(self):
        model = self.model();self.ready(model)
        self.assertTrue(model.action_reason('charged_bolt'))
        self.assertFalse(model.choose_action('charged_bolt'))
        self.assertTrue(model.set_rig_allocation(dict(weapons=3, protection=0, support=3)))
        self.assertFalse(model.action_reason('charged_bolt'))
        self.assertFalse(model.action_reason('arc_discharge'))
        self.assertTrue(model.action_reason('bulwark'))
        self.assertTrue(model.action_reason('charged_bolt', actor_id='player'))
        self.assertTrue(model.action_reason('unknown_technique'))

    def test_basic_shot_is_free_and_requires_no_specific_power(self):
        model = self.model();model.set_rig_allocation(dict(weapons=0, protection=3, support=3))
        self.ready(model);mira = model.combatant('mira');mira.mp = 0
        self.assertTrue(model.choose_action('attack'))
        self.assertEqual((model.current_action.action, mira.mp, mira.atb), ('bolt_shot', 0, 0.))
        self.assertEqual(model.actions['bolt_shot']['potency'], 1.)

    def test_commit_spends_once_and_freezes_configuration_until_action_finishes(self):
        model = self.model();model.set_rig_allocation(dict(weapons=3, protection=0, support=3))
        self.ready(model);mira = model.combatant('mira')
        self.assertTrue(model.choose_action('charged_bolt'))
        self.assertEqual((mira.mp, mira.atb), (27, 0.))
        self.assertEqual(model.rig_skill_uses, {'charged_bolt': 1})
        self.assertEqual(model.current_action.rig_allocation, model.rig_allocation)
        self.assertFalse(model.set_rig_allocation(dict(weapons=0, protection=3, support=3)))
        self.assertFalse(model.choose_action('charged_bolt'))
        self.assertEqual(mira.mp, 27)
        before = model.enemy.hp
        model.update(.649);self.assertEqual(model.enemy.hp, before)
        model.update(.001);self.assertLess(model.enemy.hp, before)

    def test_repair_target_validation_no_cost_on_cancel_or_invalid_target(self):
        model = self.model();model.set_rig_allocation(dict(weapons=0, protection=3, support=3))
        self.ready(model);mira = model.combatant('mira')
        model.player.hp = 0
        for target in (None, 'player', 'enemy', 'reserve'):
            self.assertFalse(model.choose_action('repair_pulse', target_id=target))
        self.assertEqual((mira.mp, mira.atb, model.rig_skill_uses), (30, 1., {}))
        model.player.hp = 1
        self.assertFalse(model.action_reason('repair_pulse'))
        self.assertFalse(model.choose_action('repair_pulse'))
        self.assertTrue(model.choose_action('repair_pulse', target_id='player'))
        self.assertEqual(mira.mp, 26)
        model.update(.619);self.assertEqual(model.player.hp, 1)
        model.update(.001)
        expected = healing_amount(mira.value('spr'), model.player.max_hp)
        self.assertEqual(model.player.hp, 1+expected)
        self.assertEqual(model.rig_healing, {'player': expected})
        self.assertEqual(model.rig_skill_uses, {'repair_pulse': 1})
        self.assertTrue(any(e['type'] == 'skill_heal' and e['amount'] == expected for e in model.drain_events()))

    def test_repair_clamps_to_missing_hp_and_can_target_mira(self):
        model = self.model();model.set_rig_allocation(dict(weapons=0, protection=3, support=3))
        mira = model.combatant('mira');mira.hp -= 1
        self.act(model, 'repair_pulse', 'mira')
        self.assertEqual(mira.hp, mira.max_hp)
        self.assertEqual(model.rig_healing, {'mira': 1})
        self.assertEqual(model.rig_allocation, dict(weapons=0, protection=3, support=3))

    def test_bulwark_expires_after_two_subsequent_completed_mira_actions(self):
        model = self.model();model.set_rig_allocation(dict(weapons=0, protection=3, support=3))
        mira = model.combatant('mira')
        self.act(model, 'bulwark')
        self.assertEqual((mira.barrier, mira.barrier_turns), (37, 2))
        self.ready(model);model.choose_action('guard');model.update(.499)
        self.assertEqual(mira.barrier_turns, 2)
        model.update(.001);self.assertEqual(mira.barrier_turns, 1)
        self.act(model, 'guard')
        self.assertEqual((mira.barrier, mira.barrier_turns), (0, 0))
        self.assertTrue(any(e['type'] == 'barrier_expired' and e['reason'] == 'duration'
                            for e in model.drain_events()))

    def test_barriers_refresh_and_keep_stronger_remaining_pool_without_stacking(self):
        model = self.model();mira = model.combatant('mira')
        model.set_rig_allocation(dict(weapons=3, protection=3, support=0))
        self.act(model, 'bulwark');mira.barrier = 25;mira.barrier_turns = 1
        self.act(model, 'impact_bolt', 'enemy')
        self.assertEqual((mira.barrier, mira.barrier_turns), (25, 2))
        self.act(model, 'bulwark')
        self.assertEqual((mira.barrier, mira.barrier_turns), (37, 2))

    def test_barrier_absorbs_after_guard_and_can_prevent_all_hp_damage(self):
        model = self.model();mira = model.combatant('mira')
        mira.barrier = 100;mira.barrier_turns = 2;mira.guarded = True
        before = mira.hp
        action = BattleAction('enemy', 'bite', 'mira', 'Bite', 'physical', 'bite', .72, .36)
        with patch('battle_model.roll_variance', return_value=100):
            expected = physical_damage(model.enemy, mira, 1, protected=True, variance_percent=100)
            self.assertEqual(model._damage_target(action, model.enemy, mira), 0)
        self.assertEqual(mira.hp, before)
        self.assertEqual(mira.barrier, 100-expected)
        self.assertFalse(mira.guarded)
        events = model.drain_events()
        self.assertTrue(any(e['type'] == 'impact' and e['damage'] == 0 and e['barrier_absorbed'] == expected
                            for e in events))

    def test_barrier_overflow_ko_revival_and_results_do_not_keep_protection(self):
        model = self.model();mira = model.combatant('mira')
        mira.hp = 1;mira.barrier = 1;mira.barrier_turns = 2
        action = BattleAction('enemy', 'bite', 'mira', 'Bite', 'physical', 'bite', .72, .36)
        model._damage_target(action, model.enemy, mira)
        self.assertEqual((mira.hp, mira.barrier, mira.barrier_turns), (0, 0, 0))
        mira.hp = 10;mira.barrier = 20;mira.barrier_turns = 2
        model._result('fled')
        self.assertEqual((mira.barrier, mira.barrier_turns), (0, 0))

    def test_impact_grants_its_barrier_even_when_the_attack_deals_zero(self):
        model = self.model();self.ready(model)
        self.assertTrue(model.choose_action('impact_bolt', target_id='enemy'))
        with patch.object(model, '_damage_target', return_value=0):model.update(.96)
        mira = model.combatant('mira')
        self.assertEqual((mira.barrier, mira.barrier_turns), (15, 2))

    def test_insufficient_mp_does_not_spend_turn_or_record_a_cast(self):
        model = self.model();self.ready(model);mira = model.combatant('mira');mira.mp = 3
        self.assertFalse(model.choose_action('impact_bolt', target_id='enemy'))
        self.assertEqual((mira.mp, mira.atb, model.rig_skill_uses), (3, 1., {}))

    def test_partial_absorption_preserves_remaining_damage_and_spellblade_hits_once(self):
        model = self.model();mira = model.combatant('mira')
        mira.barrier = 3;mira.barrier_turns = 2;before = mira.hp
        action = BattleAction('enemy', 'bite', 'mira', 'Bite', 'physical', 'bite', .72, .36)
        with patch('battle_model.roll_variance', return_value=100):
            damage = physical_damage(model.enemy, mira, 1, variance_percent=100)
            self.assertEqual(model._damage_target(action, model.enemy, mira), damage-3)
        self.assertEqual((mira.hp, mira.barrier, mira.barrier_turns), (before-damage+3, 0, 0))
        model.enemy.barrier = 100;model.enemy.barrier_turns = 2
        action = BattleAction('player', 'aether_edge', 'enemy', 'Aether Edge', 'spellblade', 'attack', .9, .5)
        before = model.enemy.barrier
        with patch('battle_model.roll_variance', return_value=100):
            combined = (physical_damage(model.player, model.enemy, 1, variance_percent=100)
                        +magical_damage(model.player, model.enemy, .5, variance_percent=100))
            self.assertEqual(model._damage_target(action, model.player, model.enemy), 0)
        self.assertEqual(model.enemy.barrier, before-combined)

    def test_electric_discharge_uses_magick_and_existing_enemy_absorption(self):
        model = BattleModel.from_bestiary(CharacterAttributes(), 'veylume', 3,
                                         guest_id='mira', rng=random.Random(3))
        model.set_rig_allocation(dict(weapons=3, protection=0, support=3))
        model.enemy.hp -= 20;before = model.enemy.hp
        model.enemy.barrier = 20;model.enemy.barrier_turns = 2
        self.act(model, 'arc_discharge', 'enemy')
        self.assertGreater(model.enemy.hp, before)
        self.assertEqual(model.enemy.barrier, 20)
        self.assertTrue(any(e['type'] == 'impact' and e.get('absorbed') for e in model.drain_events()))

    def test_catalog_rejects_malformed_rig_payloads(self):
        data = json.loads((Path(__file__).resolve().parents[1]/'assets/combat/actions.json').read_text())
        for identifier, field, value in (
                ('charged_bolt', 'power_requirements', dict(weapons=True, protection=0, support=0)),
                ('charged_bolt', 'power_requirements', dict(weapons=6, protection=6, support=0)),
                ('bulwark', 'barrier_turns', True),
                ('bulwark', 'barrier_percent', 0),
                ('repair_pulse', 'heal_percent', 100),
                ('repair_pulse', 'target', 'opponent'),
                ('arc_discharge', 'element', 'water')):
            malformed = deepcopy(data);malformed['actions'][identifier][field] = value
            with self.subTest(identifier=identifier, field=field), self.assertRaises(ValueError):
                load_actions(malformed)


if __name__ == '__main__':unittest.main()
