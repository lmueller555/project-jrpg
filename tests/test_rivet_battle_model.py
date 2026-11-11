"""Retired autonomous-bot behavior stays absent after Mira's rig cutover.

The filename is retained until the narrative/asset cleanup. The live rig rules
have their own detailed model suite; these checks guard the removed actor path.
"""
from copy import deepcopy
import random
import unittest

from battle_model import BattleModel, load_actions, load_enemies
from character_attributes import CharacterAttributes
from combat_damage import physical_damage


class FixedVariance:
    def __init__(self):self.calls = 0
    def randint(self, low, high):
        assert (low, high) == (95, 105)
        self.calls += 1
        return 100


class RetiredBotBattleModelTests(unittest.TestCase):
    def model(self, **options):
        enemies = {'version': 1, 'enemies': load_enemies(load_actions())}
        enemies['enemies']['bat']['attributes'].update(hp=1000000, str=0, mag=0, speed=0)
        options.setdefault('enemy_data', enemies)
        options.setdefault('guest_id', 'mira')
        options.setdefault('rng', FixedVariance())
        return BattleModel(CharacterAttributes(), **options)

    def ready_mira(self, model):
        model.player.atb = model.enemy.atb = 0
        model.combatant('mira').atb = 1
        model.update(0)
        self.assertTrue(model.select_ready('mira'))

    def test_mira_is_the_only_new_party_actor_and_never_deploys_an_attachment(self):
        for options in ({}, {'bot_loadouts': {}}, {'guest_id': None}):
            with self.subTest(options=options):
                model = self.model(**options)
                self.assertEqual(model.bots, ())
                self.assertIsNone(model.bot_for('mira'))
                self.assertIsNone(model.active_bot('mira'))
                self.assertIsNone(model.combatant('rivet'))
                self.assertFalse(any(event['type'] == 'bot_deployed' for event in model.events))
        self.assertEqual([member.identifier for member in self.model().party], ['player', 'mira'])

    def test_retired_commands_are_not_selectable_and_cannot_spend_a_turn(self):
        model = self.model()
        self.ready_mira(model)
        before = (model.phase, model.combatant('mira').mp, model.combatant('mira').atb)
        for command in ('overclock', 'piston_jab', 'deploy_rivet', 'repair_rivet'):
            with self.subTest(command=command):
                self.assertNotIn(command, model.available_actions('mira'))
                self.assertFalse(model.choose_action(command))
                self.assertEqual((model.phase, model.combatant('mira').mp,
                                  model.combatant('mira').atb), before)
                self.assertIsNone(model.current_action)

    def test_waiting_for_a_command_cannot_produce_free_autonomous_damage(self):
        model = self.model()
        self.ready_mira(model)
        before = (model.enemy.hp, model.player.atb, model.combatant('mira').atb)
        for _ in range(20):model.update(1.)
        self.assertEqual((model.enemy.hp, model.player.atb, model.combatant('mira').atb), before)
        self.assertEqual(model.rng.calls, 0)

    def test_miras_basic_shot_uses_her_own_strength_and_one_rng_draw(self):
        model = self.model()
        self.ready_mira(model)
        mira = model.combatant('mira')
        hp = model.enemy.hp
        self.assertTrue(model.choose_action('attack'))
        action = model.current_action
        self.assertEqual((action.actor, action.action), ('mira', 'bolt_shot'))
        model.update(action.duration)
        self.assertEqual(hp-model.enemy.hp, physical_damage(mira, model.enemy, 1))
        self.assertEqual(model.rng.calls, 1)
        self.assertEqual(mira.atb, 0)

    def test_rig_skills_stay_owned_by_mira_without_creating_an_extra_command_owner(self):
        model = self.model(learned_abilities=['aether_edge', 'aether_dart'])
        expected = {'charged_bolt', 'bulwark', 'repair_pulse', 'impact_bolt', 'arc_discharge'}
        self.assertEqual(set(model.skill_actions('mira')), expected)
        self.assertFalse(expected & set(model.available_actions('player')))
        self.assertEqual(model.available_actions('rivet'), [])
        self.assertEqual(model.skill_actions('rivet'), [])

    def test_large_and_small_charging_frames_reach_identical_party_ready_boundaries(self):
        left, right = self.model(), self.model()
        left.update(10.)
        for _ in range(100):right.update(.1)
        def resources(model):
            return (model.phase, model.ready_actor,
                    [(member.identifier, member.hp, member.mp, round(member.atb, 8))
                     for member in (*model.party, model.enemy)], model.bots)
        self.assertEqual(resources(left), resources(right))
        self.assertEqual(left.rng.calls, right.rng.calls)


if __name__ == '__main__':unittest.main()
