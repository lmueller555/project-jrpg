"""Wait-ATB timing, immutable entry resources and single-impact battle actions."""
from copy import deepcopy
import json
import math
import random
import unittest

from battle_model import (ACTION_PATH, ENEMY_PATH, BattleModel, load_actions,
                          load_enemies)
from character_attributes import CharacterAttributes


class FixedVariance:
    def __init__(self):self.calls = 0

    def randint(self, low, high):
        self.calls += 1
        assert (low, high) == (95, 105)
        return 100


def player(**values):
    attributes = CharacterAttributes()
    record = attributes.to_dict()
    record['attributes'].update(values)
    record['current_hp'] = record['attributes']['hp']
    record['current_mp'] = record['attributes']['mp']
    assert attributes.restore(record)
    return attributes


def enemy_data(**values):
    data = json.loads(ENEMY_PATH.read_text())
    data['enemies']['bat']['attributes'].update(values)
    return data


class BattleModelTests(unittest.TestCase):
    def model(self, attributes=None, **options):
        options.setdefault('rng', FixedVariance())
        return BattleModel(attributes or player(), **options)

    def ready(self, model):
        model.update(1000)
        self.assertTrue(model.waiting_for_player)

    def snapshot(self, model):
        actors = [(actor.hp, actor.mp, round(actor.atb, 9), actor.guarded,
                   dict(actor.attributes)) for actor in (model.player, model.enemy)]
        action = model.current_action
        active = (action.actor, action.action, round(action.elapsed, 9), action.damage,
                  action.resolved) if action else None
        return model.phase, actors, active, deepcopy(model.events)

    def test_bat_has_independent_stats_abilities_and_rewards(self):
        model = self.model()
        self.assertEqual(model.enemy.name, 'Bat')
        self.assertEqual((model.enemy.hp, model.enemy.mp), (72, 4))
        self.assertEqual(model.enemy.value('speed'), 8)
        self.assertEqual(model.enemy_definition['abilities'], ['bite', 'wing_gust'])
        self.assertEqual(model.enemy_definition['rewards'],
                         {'rp': 20, 'drops': {'aether_emerald': 1}})
        self.assertEqual(model.phase, 'charging')
        self.assertIsNone(model.current_action)
        self.assertIsNone(model.last_action)

    def test_player_entry_is_a_copy_and_combat_never_changes_source_resources(self):
        source = player()
        before = source.to_dict()
        model = self.model(source, learned_abilities=['aether_dart'])
        self.ready(model)
        self.assertTrue(model.choose_action('aether_dart'))
        model.update(100)
        self.assertLess(model.player.mp, source.current_mp)
        self.assertLess(model.player.hp, source.current_hp)
        self.assertEqual(source.to_dict(), before)
        self.assertTrue(source.set_modifiers('later', {'str': 100}))
        self.assertEqual(model.player.value('str'), 10)

    def test_every_gauge_stops_exactly_at_the_player_choice_boundary(self):
        model = self.model()
        model.update(10000)
        self.assertEqual(model.phase, 'ready')
        self.assertEqual(model.player.atb, 1)
        self.assertAlmostEqual(model.enemy.atb, .95)
        before = self.snapshot(model)
        for seconds in (.01, 3, 3600):model.update(seconds)
        self.assertEqual(self.snapshot(model), before)
        self.assertEqual(model.rng.calls, 0)

    def test_speed_controls_charge_rate_and_fast_enemy_acts_automatically(self):
        model = self.model(enemy_data=enemy_data(speed=20))
        model.update(4.999)
        self.assertEqual(model.phase, 'charging')
        model.update(.001)
        self.assertEqual(model.phase, 'acting')
        self.assertEqual(model.current_action.actor, 'enemy')
        self.assertEqual(model.current_action.action, 'bite')
        self.assertAlmostEqual(model.player.atb, .8)
        self.assertEqual(model.enemy.atb, 0)
        self.assertEqual(model.player.hp, 140)

    def test_simultaneous_readiness_gives_player_first_choice_then_enemy_turn(self):
        model = self.model(enemy_data=enemy_data(speed=10))
        model.update(6.25)
        self.assertEqual(model.phase, 'ready')
        self.assertEqual(model.enemy.atb, 1)
        self.assertFalse(any(event['type'] == 'action_started' for event in model.events))
        model.choose_action('attack')
        model.update(model.current_action.duration)
        self.assertEqual(model.current_action.actor, 'enemy')
        self.assertEqual(model.current_action.elapsed, 0)

    def test_dead_enemy_cannot_execute_its_queued_ready_turn(self):
        model = self.model(enemy_data=enemy_data(speed=10, hp=1))
        self.ready(model);model.choose_action('attack');model.update(1000)
        self.assertEqual(model.phase, 'victory')
        self.assertEqual(model.player.hp, 140)
        self.assertEqual(model.rng.calls, 1)
        self.assertFalse(any(event.get('actor') == 'enemy' for event in model.events))

    def test_large_frames_and_small_frames_reach_the_same_first_choice(self):
        large = self.model()
        small = self.model()
        large.update(20)
        for _ in range(2000):small.update(.01)
        self.assertEqual(self.snapshot(large), self.snapshot(small))

    def test_large_frames_and_small_frames_match_through_action_and_enemy_turn(self):
        large, small = self.model(), self.model()
        self.ready(large);self.ready(small)
        large.choose_action('attack');small.choose_action('attack')
        large.update(3)
        for _ in range(300):small.update(.01)
        self.assertEqual(self.snapshot(large), self.snapshot(small))
        self.assertEqual(large.rng.calls, small.rng.calls)

    def test_damage_occurs_at_impact_once_and_gauges_freeze_during_action(self):
        model = self.model()
        self.ready(model);model.choose_action('attack')
        atb = model.player.atb, model.enemy.atb
        model.update(.35)
        self.assertEqual(model.enemy.hp, 72)
        self.assertEqual((model.player.atb, model.enemy.atb), atb)
        model.update(.01)
        self.assertEqual(model.enemy.hp, 54)
        self.assertEqual(model.current_action.damage, 18)
        self.assertTrue(model.current_action.resolved)
        self.assertEqual((model.player.atb, model.enemy.atb), atb)
        model.update(.01)
        self.assertEqual(model.enemy.hp, 54)
        self.assertEqual(model.rng.calls, 1)
        hits = [event for event in model.events if event['type'] == 'impact']
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]['target'], 'enemy')
        self.assertEqual(hits[0]['remaining_hp'], 54)

    def test_victory_waits_for_the_ending_animation_and_then_freezes(self):
        model = self.model(enemy_data=enemy_data(hp=1))
        self.ready(model);model.choose_action('attack')
        model.update(.36)
        self.assertEqual(model.enemy.hp, 0)
        self.assertEqual(model.phase, 'acting')
        model.update(.36)
        self.assertEqual(model.phase, 'victory')
        self.assertTrue(model.ended)
        self.assertIsNone(model.current_action)
        self.assertEqual(model.last_action.action, 'attack')
        before = self.snapshot(model)
        model.update(10000)
        self.assertFalse(model.choose_action('attack'))
        self.assertEqual(self.snapshot(model), before)

    def test_invalid_time_is_rejected_without_mutation(self):
        model = self.model()
        before = self.snapshot(model)
        for bad in (True, None, [], '1', -1, math.inf, math.nan):
            with self.subTest(seconds=bad):
                with self.assertRaises((TypeError, ValueError)):model.update(bad)
                self.assertEqual(self.snapshot(model), before)

    def test_unready_unknown_and_unlearned_commands_never_spend_or_change_gauges(self):
        model = self.model()
        before = self.snapshot(model)
        self.assertFalse(model.choose_action('attack'))
        self.assertEqual(self.snapshot(model), before)
        self.ready(model)
        before = self.snapshot(model)
        for identifier in ('unknown', 'aether_dart', 'mend', None, [], True):
            with self.subTest(action=identifier):
                self.assertFalse(model.choose_action(identifier))
                self.assertEqual(self.snapshot(model), before)
        self.assertEqual(model.available_actions(), ['attack', 'guard', 'flee'])

    def test_learned_dart_charges_mp_at_commit_and_uses_magick_damage(self):
        model = self.model(learned_abilities=['basic_magicks', 'mend', 'aether_dart'])
        self.assertEqual(model.available_actions(), ['attack', 'guard', 'flee', 'aether_dart'])
        self.ready(model)
        self.assertTrue(model.choose_action('aether_dart'))
        self.assertEqual(model.player.mp, 26)
        self.assertEqual(model.enemy.hp, 72)
        model.update(.5)
        self.assertEqual(model.enemy.hp, 34)  # 20*2*10²/(100+5) floors to 38.
        self.assertEqual(model.current_action.kind, 'magical')
        before = self.snapshot(model)
        self.assertFalse(model.choose_action('aether_dart'))
        self.assertEqual(self.snapshot(model), before)

    def test_unaffordable_learned_dart_preserves_the_ready_turn(self):
        attributes = player()
        self.assertTrue(attributes.set_current(mp=3))
        model = self.model(attributes, learned_abilities=['aether_dart'])
        self.ready(model)
        before = self.snapshot(model)
        self.assertIn('MP', model.action_reason('aether_dart'))
        self.assertFalse(model.choose_action('aether_dart'))
        self.assertEqual(self.snapshot(model), before)
        self.assertTrue(model.choose_action('attack'))

    def test_enemy_alternates_bite_and_gust_then_uses_free_fallback(self):
        model = self.model(player(hp=9999), enemy_data=enemy_data(hp=9999))
        actions = []
        for _ in range(10):
            self.ready(model);model.choose_action('guard');model.update(1000)
            for event in model.drain_events():
                if event['type'] == 'action_started' and event['actor'] == 'enemy':
                    actions.append(event['action'])
        self.assertEqual(actions[:6], ['bite', 'wing_gust', 'bite', 'wing_gust', 'bite', 'bite'])
        self.assertTrue(all(action == 'bite' for action in actions[4:]))
        self.assertEqual(model.enemy.mp, 0)

    def test_guard_halves_one_incoming_action_and_does_not_refill_resources(self):
        model = self.model()
        self.ready(model)
        before_mp = model.player.mp
        model.choose_action('guard');model.update(.2)
        self.assertTrue(model.player.guarded)
        self.assertEqual(model.player.hp, 140)
        self.assertEqual(model.player.mp, before_mp)
        model.update(1000)
        self.assertFalse(model.player.guarded)
        guarded = [event for event in model.events if event['type'] == 'impact'
                   and event['target'] == 'player']
        self.assertEqual(guarded[0]['damage'], 4)  # Bite's unguarded damage is 8.
        self.assertTrue(guarded[0]['guarded'])
        self.assertEqual(model.player.hp, 136)

    def test_flee_consumes_one_turn_then_ends_without_inflicting_damage(self):
        model = self.model(enemy_data=enemy_data(speed=10))
        self.ready(model);model.choose_action('flee')
        self.assertEqual(model.player.atb, 0)
        model.update(.35)
        self.assertEqual(model.phase, 'acting')
        model.update(.35)
        self.assertEqual(model.phase, 'fled')
        self.assertEqual((model.player.hp, model.enemy.hp), (140, 72))
        self.assertEqual(model.rng.calls, 0)

    def test_enemy_damage_can_defeat_player_without_negative_hp_or_another_turn(self):
        source = player();self.assertTrue(source.set_current(hp=1))
        model = self.model(source, enemy_data=enemy_data(speed=20))
        model.update(100)
        self.assertEqual(model.phase, 'defeat')
        self.assertEqual(model.player.hp, 0)
        self.assertEqual(source.current_hp, 1)
        before = self.snapshot(model)
        model.update(100)
        self.assertEqual(self.snapshot(model), before)

    def test_dead_player_starts_at_defeat_and_cannot_take_actions(self):
        source = player();self.assertTrue(source.set_current(hp=0))
        model = self.model(source)
        self.assertEqual(model.phase, 'defeat')
        self.assertTrue(model.ended)
        self.assertFalse(model.choose_action('attack'))
        self.assertEqual(model.enemy.hp, 72)

    def test_seeded_battles_are_reproducible_and_can_award_no_resources_themselves(self):
        first = BattleModel(player(), rng=random.Random(982))
        second = BattleModel(player(), rng=random.Random(982))
        for model in (first, second):
            while not model.ended:
                model.update(1000)
                if model.waiting_for_player:model.choose_action('attack')
        self.assertEqual(self.snapshot(first), self.snapshot(second))
        self.assertEqual(first.phase, 'victory')
        self.assertFalse(hasattr(first, 'inventory'))
        self.assertFalse(hasattr(first, 'lattice'))

    def test_drain_events_preserves_order_and_does_not_replay_impacts(self):
        model = self.model()
        self.ready(model);model.choose_action('attack');model.update(.36)
        events = model.drain_events()
        self.assertEqual([event['type'] for event in events],
                         ['player_ready', 'action_started', 'impact'])
        self.assertEqual(model.drain_events(), [])
        model.update(.01)
        self.assertEqual(model.drain_events(), [])

    def test_future_enemy_health_and_mp_are_independent_of_party_resource_caps(self):
        model = self.model(enemy_data=enemy_data(hp=1000000, mp=10000))
        self.assertEqual(model.enemy.max_hp, 1000000)
        self.assertEqual(model.enemy.max_mp, 10000)
        self.assertEqual(model.player.max_hp, 140)
        self.ready(model);model.choose_action('attack');model.update(.36)
        self.assertEqual(model.enemy.hp, 999982)

    def test_damage_uses_the_approved_per_hit_cap(self):
        actions = json.loads(ACTION_PATH.read_text())
        actions['actions']['attack']['potency'] = 12
        model = self.model(player(str=255), enemy_data=enemy_data(hp=1000000),
                           action_data=actions)
        self.ready(model);model.choose_action('attack');model.update(.36)
        self.assertEqual(model.current_action.damage, 9999)
        self.assertEqual(model.enemy.hp, 990001)

    def test_catalogs_copy_inputs_and_reject_invalid_values(self):
        actions = json.loads(ACTION_PATH.read_text())
        enemies = enemy_data()
        original_actions, original_enemies = deepcopy(actions), deepcopy(enemies)
        parsed_actions = load_actions(actions)
        parsed_enemies = load_enemies(parsed_actions, enemies)
        parsed_actions['attack']['mp_cost'] = 99
        parsed_enemies['bat']['attributes']['hp'] = 1
        self.assertEqual(actions, original_actions)
        self.assertEqual(enemies, original_enemies)
        for field, value in (('duration', 0), ('duration', math.inf), ('potency', True),
                             ('mp_cost', -1), ('impact_at', 100), ('target', 'self')):
            bad = deepcopy(actions);bad['actions']['attack'][field] = value
            with self.subTest(action_field=field, value=value):
                with self.assertRaises(ValueError):load_actions(bad)
        for field, value in (('hp', 0), ('mp', -1), ('str', 256), ('speed', True)):
            bad = deepcopy(enemies);bad['enemies']['bat']['attributes'][field] = value
            with self.subTest(enemy_field=field, value=value):
                with self.assertRaises(ValueError):load_enemies(load_actions(), bad)

    def test_enemy_requires_free_fallback_and_rewards_are_strict(self):
        actions = load_actions()
        for abilities in (['wing_gust'], ['bite', 'bite'], ['guard'], ['missing'], []):
            bad = enemy_data();bad['enemies']['bat']['abilities'] = abilities
            with self.subTest(abilities=abilities):
                with self.assertRaises(ValueError):load_enemies(actions, bad)
        for rewards in ({'rp': True, 'drops': {}}, {'rp': 20, 'drops': {'aether_emerald': 0}},
                        {'rp': 20, 'drops': [], 'extra': 1}):
            bad = enemy_data();bad['enemies']['bat']['rewards'] = rewards
            with self.subTest(rewards=rewards):
                with self.assertRaises(ValueError):load_enemies(actions, bad)


if __name__ == '__main__':unittest.main()
