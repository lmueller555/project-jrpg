"""Real party readiness, individual resources and the Tusker's readable charge."""
from copy import deepcopy
import json
import random
import unittest

from battle_model import (BattleModel, ENEMY_PATH, GUEST_PATH, load_actions,
                          load_enemies, load_guests)
from character_attributes import CharacterAttributes


class FixedVariance:
    def randint(self, low, high):
        assert (low, high) == (95, 105)
        return 100


class PartyBattleModelTests(unittest.TestCase):
    def model(self, source=None, **options):
        options.setdefault('rng', FixedVariance())
        options.setdefault('guest_id', 'mira')
        options.setdefault('enemy_id', 'ridgeback_tusker')
        return BattleModel(source or CharacterAttributes(), **options)

    @staticmethod
    def snapshot(model):
        return (model.phase, model.ready_actor, model.telegraphed_target,
                [(member.identifier, member.hp, member.mp, round(member.atb, 9),
                  member.guarded) for member in (*model.party, model.enemy)],
                deepcopy(model.current_action), deepcopy(model.events))

    def test_guest_is_a_separate_fixed_profile_with_meaningfully_stronger_weapon(self):
        source = CharacterAttributes()
        before = source.to_dict()
        model = self.model(source)
        self.assertEqual([member.identifier for member in model.party], ['player', 'mira'])
        mira = model.combatant('mira')
        self.assertEqual((mira.hp, mira.mp, mira.value('str')), (300, 30, 20))
        self.assertEqual(model.enemy.hp, 450)
        self.assertEqual(model.enemy_definition['abilities'],
                         ['tusk_strike', 'prepare_charge', 'tusker_charge'])
        model.update(1000)
        self.assertEqual(model.ready_actor, 'mira')
        self.assertEqual(model.available_actions(), ['attack', 'guard', 'flee'])
        self.assertTrue(model.choose_action('attack'))
        self.assertEqual(model.current_action.action, 'spear_thrust')
        model.update(.4)
        self.assertEqual(model.current_action.damage, 101)
        model.update(1000)
        self.assertEqual(model.ready_actor, 'player')
        self.assertTrue(model.choose_action('attack'))
        model.update(.36)
        self.assertEqual(model.current_action.damage, 16)
        self.assertEqual(source.to_dict(), before)

    def test_every_gauge_freezes_at_miras_exact_ready_boundary(self):
        model = self.model()
        model.update(1000)
        self.assertEqual(model.phase, 'ready')
        self.assertEqual(model.active_player.name, 'Mira')
        self.assertEqual(model.combatant('mira').atb, 1)
        self.assertAlmostEqual(model.player.atb, .16/.168)
        self.assertAlmostEqual(model.enemy.atb, .152/.168)
        before = self.snapshot(model)
        for seconds in (.1, 7, 10000):model.update(seconds)
        self.assertEqual(self.snapshot(model), before)
        self.assertEqual(model.events, [{'type': 'player_ready', 'actor': 'mira'}])

    def test_simultaneous_party_readiness_allows_selection_before_enemy_turn(self):
        guests = json.loads(GUEST_PATH.read_text())
        guests['guests']['mira']['attributes']['speed'] = 10
        enemies = json.loads(ENEMY_PATH.read_text())
        enemies['enemies']['ridgeback_tusker']['attributes']['speed'] = 10
        model = self.model(guest_data=guests, enemy_data=enemies)
        model.update(6.25)
        self.assertEqual(model.ready_members, ('player', 'mira'))
        self.assertTrue(model.select_ready('mira'))
        self.assertEqual(model.active_player.name, 'Mira')
        self.assertEqual(model.enemy.atb, 1)
        model.choose_action('attack')
        model.update(.8)
        self.assertEqual(model.phase, 'ready')
        self.assertEqual(model.ready_actor, 'player')
        self.assertFalse(any(event['type'] == 'action_started' and event['actor'] == 'enemy'
                             for event in model.events))
        model.choose_action('guard')
        model.update(.5)
        self.assertEqual(model.current_action.actor, 'enemy')

    def test_unready_dead_or_unknown_member_cannot_take_a_ready_turn(self):
        model = self.model()
        model.update(1000)
        before = self.snapshot(model)
        for actor in ('player', 'enemy', 'missing', [], True):
            with self.subTest(actor=actor):
                self.assertFalse(model.select_ready(actor))
                self.assertFalse(model.choose_action('attack', actor_id=actor))
                self.assertEqual(self.snapshot(model), before)

    def test_guest_attack_and_caelans_spell_spend_only_their_own_resources(self):
        source = CharacterAttributes()
        model = self.model(source, learned_abilities=['aether_dart'])
        model.player.atb = model.combatant('mira').atb = 1
        model.update(0)
        self.assertTrue(model.select_ready('mira'))
        self.assertNotIn('aether_dart', model.available_actions())
        model.choose_action('attack')
        self.assertEqual(model.player.atb, 1)
        self.assertEqual(model.combatant('mira').atb, 0)
        model.update(.8)
        self.assertEqual(model.ready_actor, 'player')
        self.assertIn('aether_dart', model.available_actions())
        model.choose_action('aether_dart')
        self.assertEqual((model.player.mp, model.combatant('mira').mp), (26, 30))
        self.assertEqual(source.current_mp, 30)

    def test_preparation_is_a_separate_turn_with_a_real_guard_opportunity(self):
        model = self.model()
        history, guarded_ready = [], False
        for _ in range(30):
            model.update(1000)
            history.extend(model.drain_events())
            if any(event['type'] == 'impact' and event['action'] == 'tusker_charge'
                   for event in history):break
            self.assertTrue(model.waiting_for_player)
            if model.ready_actor == 'player' and model.telegraphed_target == 'player':
                guarded_ready = True
                model.choose_action('guard')
            else:model.choose_action('attack')
        self.assertTrue(guarded_ready)
        tell = next(event for event in history if event['type'] == 'telegraph')
        hit = next(event for event in history if event['type'] == 'impact'
                   and event['action'] == 'tusker_charge')
        self.assertEqual(tell['target'], 'player')
        self.assertEqual(hit['target'], 'player')
        self.assertEqual(hit['damage'], 34)
        self.assertTrue(hit['guarded'])
        self.assertFalse(any(event['type'] == 'impact' and event['action'] == 'prepare_charge'
                             for event in history))
        self.assertIsNone(model.telegraphed_target)
        self.assertGreater(model.player.hp, 0)

    def test_guard_is_individual_and_preparation_does_not_consume_it(self):
        model = self.model()
        model.player.guarded = True
        model._start_action('enemy', 'prepare_charge')
        model.update(.4)
        self.assertTrue(model.player.guarded)
        self.assertEqual(model.player.hp, 140)
        self.assertEqual(model.telegraphed_target, 'player')
        model.update(.4)
        model._start_action('enemy', 'tusk_strike')
        model.update(.45)
        self.assertTrue(model.player.guarded)
        self.assertEqual(model.player.hp, 140)
        self.assertEqual(model.combatant('mira').hp, 257)

    def test_incapped_caelan_does_not_end_battle_while_mira_can_act(self):
        source = CharacterAttributes()
        self.assertTrue(source.set_current(hp=0))
        enemies = json.loads(ENEMY_PATH.read_text())
        enemies['enemies']['ridgeback_tusker']['attributes']['hp'] = 1
        model = self.model(source, enemy_data=enemies)
        self.assertEqual(model.phase, 'charging')
        model.update(1000)
        self.assertEqual(model.ready_actor, 'mira')
        self.assertEqual(model.player.atb, 0)
        model.choose_action('attack');model.update(1000)
        self.assertEqual(model.phase, 'victory')
        self.assertEqual(model.player.hp, 0)

    def test_party_defeat_waits_until_every_living_member_is_incapacitated(self):
        source = CharacterAttributes()
        self.assertTrue(source.set_current(hp=0))
        guests = json.loads(GUEST_PATH.read_text())
        guests['guests']['mira']['attributes']['hp'] = 1
        enemies = json.loads(ENEMY_PATH.read_text())
        enemies['enemies']['ridgeback_tusker']['attributes'].update(str=255, speed=255)
        model = self.model(source, guest_data=guests, enemy_data=enemies)
        model.update(1000)
        self.assertEqual(model.phase, 'defeat')
        self.assertTrue(all(member.hp == 0 for member in model.party))
        self.assertTrue(all(member.atb == 0 for member in model.party))

    def test_enemy_retargets_living_mira_if_charge_target_has_fallen(self):
        model = self.model()
        model.telegraphed_target = 'player'
        model.player.hp = 0
        model._start_action('enemy', 'tusker_charge')
        self.assertEqual(model.current_action.target, 'mira')
        model.update(.5)
        self.assertLess(model.combatant('mira').hp, 300)
        self.assertEqual(model.player.hp, 0)
        self.assertIsNone(model.telegraphed_target)

    def test_either_party_member_can_withdraw_the_party(self):
        model = self.model()
        model.update(1000)
        self.assertEqual(model.ready_actor, 'mira')
        self.assertTrue(model.choose_action('flee'))
        model.update(.7)
        self.assertEqual(model.phase, 'fled')
        self.assertEqual([member.hp for member in model.party], [140, 300])
        self.assertEqual(model.enemy.hp, 450)

    def test_large_and_small_updates_match_through_party_and_enemy_turns(self):
        large = self.model(rng=random.Random(71))
        small = self.model(rng=random.Random(71))
        for _ in range(8):
            large.update(1000)
            for _ in range(100000):
                if small.waiting_for_player or small.ended:break
                small.update(.01)
            self.assertEqual(self.snapshot(large), self.snapshot(small))
            if large.ended:break
            action = ('guard' if large.ready_actor == large.telegraphed_target else 'attack')
            large.choose_action(action);small.choose_action(action)

    def test_guest_catalogs_are_copied_and_reject_invalid_actor_profiles(self):
        data = json.loads(GUEST_PATH.read_text())
        before = deepcopy(data)
        parsed = load_guests(load_actions(), data)
        parsed['mira']['attributes']['str'] = 1
        self.assertEqual(data, before)
        for field, value in (('hp', 0), ('hp', 10000), ('mp', 1000), ('str', 256),
                              ('speed', True)):
            bad = deepcopy(data);bad['guests']['mira']['attributes'][field] = value
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError):self.model(guest_data=bad)
        for attack in ('guard', 'missing', [], True):
            bad = deepcopy(data);bad['guests']['mira']['attack'] = attack
            with self.subTest(attack=attack):
                with self.assertRaises(ValueError):load_guests(load_actions(), bad)
        with self.assertRaises(ValueError):self.model(guest_id='missing')
        bad = deepcopy(data);bad['guests']['player'] = bad['guests'].pop('mira')
        with self.assertRaises(ValueError):load_guests(load_actions(), bad)

    def test_enemy_cannot_have_only_nondamaging_preparation_actions(self):
        data = json.loads(ENEMY_PATH.read_text())
        data['enemies']['ridgeback_tusker']['abilities'] = ['prepare_charge']
        with self.assertRaises(ValueError):load_enemies(load_actions(), data)


if __name__ == '__main__':unittest.main()
