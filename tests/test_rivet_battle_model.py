"""Owner-bound autonomous ATB, Overclock lifetime, and untargetable bot rules."""
from copy import deepcopy
import json
import random
import unittest

from battle_model import (ACTION_PATH, BOT_PATH, ENEMY_PATH, GUEST_PATH, BattleModel, BotUnit,
                          load_actions, load_bots)
from character_attributes import CharacterAttributes
from combat_damage import physical_damage


class FixedVariance:
    def __init__(self):self.calls = 0

    def randint(self, low, high):
        assert (low, high) == (95, 105)
        self.calls += 1
        return 100


class RivetBattleModelTests(unittest.TestCase):
    def model(self, **options):
        enemies = json.loads(ENEMY_PATH.read_text())
        enemies['enemies']['bat']['attributes'].update(hp=1000000, str=0, mag=0, speed=0)
        options.setdefault('enemy_data', enemies)
        options.setdefault('guest_id', 'mira')
        options.setdefault('rng', FixedVariance())
        return BattleModel(CharacterAttributes(), **options)

    def ready_mira(self, model):
        self.assertIsNone(model.current_action)
        model.player.atb = model.enemy.atb = 0
        model.combatant('mira').atb = 1
        model.update(0)
        self.assertTrue(model.waiting_for_player)
        self.assertTrue(model.select_ready('mira'))

    def overclock(self, model):
        self.ready_mira(model)
        self.assertTrue(model.choose_action('overclock'))
        model.update(.9)

    def bot_turn(self, model):
        self.assertEqual(model.phase, 'charging')
        model.player.atb = model.combatant('mira').atb = model.enemy.atb = 0
        model.bot_for().atb = 1
        model.update(0)
        self.assertEqual(model.current_action.actor, 'rivet')
        action = model.current_action
        model.update(action.duration)
        return action

    def snapshot(self, model):
        actors = [(actor.identifier, actor.hp, actor.mp, round(actor.atb, 9))
                  for actor in (*model.party, model.enemy)]
        bots = [(bot.identifier, round(bot.atb, 9), bot.haste_turns)
                for bot in model.bots]
        action = model.current_action
        active = (action.actor, action.action, round(action.elapsed, 9),
                  action.damage, action.resolved) if action else None
        events = [{key: value for key, value in event.items() if key != 'frame_age'}
                  for event in model.events]
        return model.phase, actors, bots, active, deepcopy(events)

    def test_mira_deploys_one_free_resource_less_attachment_at_empty_atb(self):
        model = self.model()
        bot = model.bot_for()
        self.assertIsInstance(bot, BotUnit)
        self.assertIs(model.combatant('rivet'), bot)
        self.assertIs(model.active_bot(), bot)
        self.assertEqual((bot.identifier, bot.owner_id, bot.ability_id),
                         ('rivet', 'mira', 'piston_jab'))
        self.assertEqual((bot.atb, bot.haste_turns), (0, 0))
        self.assertFalse({'hp', 'mp'} & set(bot.attributes))
        self.assertFalse(hasattr(bot, 'hp'))
        self.assertFalse(hasattr(bot, 'mp'))
        self.assertEqual([member.identifier for member in model.party], ['player', 'mira'])
        self.assertEqual([member.mp for member in model.party], [30, 30])
        self.assertEqual(model.events, [{'type': 'bot_deployed', 'actor': 'rivet',
                                        'owner': 'mira'}])
        self.assertNotIn('deploy', model.available_actions('mira'))
        self.assertNotIn('repair', model.available_actions('mira'))

    def test_no_mira_and_explicit_empty_loadout_do_not_deploy(self):
        self.assertEqual(self.model(guest_id=None).bots, ())
        self.assertEqual(self.model(bot_loadouts={}).bots, ())
        self.assertIsNone(self.model(guest_id=None).active_bot())
        self.assertIsNot(self.model().bot_for(), self.model().bot_for())

    def test_skills_are_actor_specific_and_overclock_requires_bot_not_weapon(self):
        model = self.model(learned_abilities=['aether_edge', 'overclock', 'aether_dart'],
                           guest_abilities={'mira': ['overclock', 'aether_edge', 'aether_dart']})
        self.assertEqual(model.skill_actions('player'), ['aether_edge'])
        self.assertEqual(model.skill_actions('mira'), ['overclock'])
        self.assertNotIn('aether_dart', model.available_actions('mira'))
        self.assertNotIn('overclock', model.available_actions('player'))
        self.assertEqual(model.available_actions('rivet'), [])
        self.ready_mira(model)
        self.assertEqual(model.command_reason('skills'), '')
        self.assertEqual(model.action_reason('overclock'), '')
        self.assertTrue(model.choose_action('overclock'))
        missing = self.model(bot_loadouts={})
        self.ready_mira(missing)
        self.assertEqual(missing.action_reason('overclock'), 'Requires an active bot.')
        self.assertFalse(missing.choose_action('overclock'))
        unlearned = self.model(guest_abilities={'mira': []})
        self.assertEqual(unlearned.skill_actions('mira'), [])

    def test_overclock_spends_normal_turn_and_applies_at_impact_preserving_fraction(self):
        model = self.model()
        bot = model.bot_for()
        bot.atb = .37
        self.ready_mira(model)
        model.enemy.atb = .64
        self.assertTrue(model.choose_action('overclock'))
        self.assertEqual((model.combatant('mira').mp, model.combatant('mira').atb), (25, 0))
        self.assertEqual((model.current_action.kind, model.current_action.target,
                          model.current_action.animation), ('haste', 'rivet', 'overclock'))
        model.update(.499)
        self.assertEqual((bot.atb, bot.haste_turns, model.enemy.atb), (.37, 0, .64))
        model.update(.001)
        self.assertEqual((bot.atb, bot.haste_turns), (.37, 8))
        self.assertAlmostEqual(model.atb_rate(bot), (.12+.004*8)*1.5)
        self.assertEqual(model.rng.calls, 0)
        model.update(.4)
        self.assertEqual(bot.atb, .37)
        self.assertEqual(model.combatant('mira').atb, 0)
        applied = [event for event in model.events if event['type'] == 'haste_applied']
        self.assertEqual(applied, [{'type': 'haste_applied', 'actor': 'mira',
                                   'target': 'rivet', 'action': 'overclock',
                                   'remaining_turns': 8, 'rate_multiplier': 1.5}])

    def test_unaffordable_overclock_preserves_mp_and_ready_turn(self):
        model = self.model()
        model.combatant('mira').mp = 4
        self.ready_mira(model)
        before = self.snapshot(model)
        self.assertEqual(model.action_reason('overclock'), 'Not enough MP.')
        self.assertFalse(model.choose_action('overclock'))
        self.assertEqual(self.snapshot(model), before)

    def test_haste_expires_on_eighth_completed_bot_action_and_refreshes_to_eight(self):
        model = self.model()
        self.overclock(model)
        bot = model.bot_for()
        for expected in (7, 6, 5):
            self.bot_turn(model)
            self.assertEqual(bot.haste_turns, expected)
        bot.atb = .42
        self.overclock(model)
        self.assertEqual((bot.haste_turns, bot.atb), (8, .42))
        self.assertEqual(model.combatant('mira').mp, 20)
        for expected in range(7, -1, -1):
            self.bot_turn(model)
            self.assertEqual(bot.haste_turns, expected)
        self.assertEqual(bot.atb, 0)
        self.assertAlmostEqual(model.atb_rate(bot), .12+.004*8)
        self.bot_turn(model)
        self.assertEqual(bot.haste_turns, 0)
        self.assertEqual(len([event for event in model.events
                              if event['type'] == 'haste_expired']), 1)

    def test_haste_does_not_tick_at_impact_or_for_other_actors_or_choice_time(self):
        model = self.model()
        self.overclock(model)
        bot = model.bot_for()
        self.ready_mira(model)
        before = self.snapshot(model)
        model.update(100000)
        self.assertEqual(self.snapshot(model), before)
        model.choose_action('attack')
        model.update(.8)
        self.assertEqual(bot.haste_turns, 8)
        model.player.atb = model.combatant('mira').atb = model.enemy.atb = 0
        bot.atb = 1
        model.update(0)
        model.update(.4)
        self.assertEqual(bot.haste_turns, 8)
        model.update(.399)
        self.assertEqual(bot.haste_turns, 8)
        model.update(.001)
        self.assertEqual(bot.haste_turns, 7)

    def test_ties_choose_party_in_order_then_bot_then_enemy_sequentially(self):
        model = self.model()
        for actor in (*model.party, *model.bots, model.enemy):actor.atb = 1
        model.update(0)
        self.assertEqual(model.ready_actor, 'player')
        model.choose_action('guard');model.update(model.current_action.duration)
        self.assertEqual(model.ready_actor, 'mira')
        model.choose_action('guard');model.update(model.current_action.duration)
        self.assertEqual((model.current_action.actor, model.current_action.elapsed), ('rivet', 0))
        model.update(.8)
        self.assertEqual((model.current_action.actor, model.current_action.elapsed), ('enemy', 0))
        starts = [event['actor'] for event in model.events if event['type'] == 'action_started']
        self.assertEqual(starts, ['player', 'mira', 'rivet', 'enemy'])

    def test_bot_gauge_freezes_during_every_animation_and_ready_menu(self):
        model = self.model()
        model.update(1000)
        bot = model.bot_for()
        before = self.snapshot(model)
        model.update(1000)
        self.assertEqual(self.snapshot(model), before)
        gauge = bot.atb
        model.choose_action('attack')
        model.update(.4)
        self.assertEqual(bot.atb, gauge)
        model.update(.399)
        self.assertEqual(bot.atb, gauge)

    def test_owner_ko_suspends_bot_and_revive_resumes_fraction_and_counter(self):
        model = self.model()
        self.overclock(model)
        bot = model.bot_for()
        bot.atb = .63
        mira = model.combatant('mira')
        mira.hp = 1
        model.enemy_id = 'ridgeback_tusker'
        model.enemy_definition['abilities'] = ['tusk_strike']
        model.enemy.atb = 1
        model.update(0)
        model.update(.9)
        self.assertEqual(mira.hp, 0)
        self.assertIsNone(model.active_bot())
        self.assertEqual((bot.atb, bot.haste_turns), (.63, 8))
        model.player.atb = 1
        model.update(1000)
        model.choose_action('guard');model.update(model.current_action.duration)
        self.assertEqual((bot.atb, bot.haste_turns), (.63, 8))
        mira.hp = 10
        model.update(0)
        self.assertIs(model.active_bot(), bot)
        self.assertEqual((bot.atb, bot.haste_turns), (.63, 8))
        model.update(.1)
        self.assertAlmostEqual(bot.atb, .63+.1*(.12+.004*8)*1.5)
        transitions = [event['type'] for event in model.events
                       if event['type'] in ('bot_suspended', 'bot_resumed')]
        self.assertEqual(transitions, ['bot_suspended', 'bot_resumed'])

    def test_owner_ko_during_bot_action_suspends_its_impact_and_completed_turn(self):
        model = self.model()
        self.overclock(model)
        bot = model.bot_for()
        bot.atb = 1
        model.update(0)
        action = model.current_action
        model.update(.2)
        model.combatant('mira').hp = 0
        gauges = [actor.atb for actor in (*model.party, bot, model.enemy)]
        enemy_hp = model.enemy.hp
        model.update(1000)
        self.assertEqual((action.elapsed, action.resolved, bot.haste_turns), (.2, False, 8))
        self.assertEqual(model.enemy.hp, enemy_hp)
        self.assertEqual([actor.atb for actor in (*model.party, bot, model.enemy)], gauges)
        model.combatant('mira').hp = 1
        model.update(.2)
        self.assertTrue(action.resolved)
        self.assertEqual(bot.haste_turns, 8)
        model.update(.4)
        self.assertEqual(bot.haste_turns, 7)

        doomed = self.model()
        doomed.bot_for().atb = 1
        doomed.update(0)
        for member in doomed.party:member.hp = 0
        doomed.update(1000)
        self.assertEqual(doomed.phase, 'defeat')
        self.assertIsNone(doomed.current_action)
        self.assertEqual(doomed.bots, ())

    def test_enemy_targeting_and_defeat_never_include_the_bot(self):
        model = self.model()
        model.telegraphed_target = 'rivet'
        self.assertEqual(model._enemy_target('tusker_charge'), 'player')
        for identifier in model.enemy_definition['abilities']:
            self.assertIn(model._enemy_target(identifier), ('player', 'mira'))
        bot = model.bot_for()
        bot.atb, bot.haste_turns = .99, 8
        for member in model.party:member.hp = 0
        model.update(0)
        self.assertEqual(model.phase, 'defeat')
        self.assertEqual(model.bots, ())
        self.assertEqual((bot.atb, bot.haste_turns), (0, 0))
        self.assertIsNone(model.active_bot())

    def test_piston_jab_is_one_physical_hit_using_mira_strength_with_normal_cap(self):
        model = self.model()
        mira = model.combatant('mira')
        mira.attributes['str'] = 30
        action = self.bot_turn(model)
        self.assertEqual(action.damage, physical_damage(mira, model.enemy))
        self.assertEqual(model.rng.calls, 1)
        impacts = [event for event in model.events if event['type'] == 'impact']
        self.assertEqual(len(impacts), 1)
        self.assertEqual((impacts[0]['actor'], impacts[0]['target']), ('rivet', 'enemy'))
        catalog = json.loads(ACTION_PATH.read_text())
        catalog['actions']['piston_jab']['potency'] = 100
        capped = self.model(action_data=catalog)
        capped.combatant('mira').attributes['str'] = 255
        self.assertEqual(self.bot_turn(capped).damage, 9999)
        self.assertEqual(capped.bot_for().attributes['str'], 255)

    def test_results_clear_bot_state_and_next_battle_starts_empty(self):
        for outcome in ('victory', 'fled'):
            with self.subTest(outcome=outcome):
                model = self.model()
                self.overclock(model)
                bot = model.bot_for()
                bot.atb = .8
                self.ready_mira(model)
                if outcome == 'victory':model.enemy.hp = 1
                model.choose_action('attack' if outcome == 'victory' else 'flee')
                model.update(.8)
                self.assertEqual(model.phase, outcome)
                self.assertEqual(model.bots, ())
                self.assertEqual((bot.atb, bot.haste_turns), (0, 0))
                self.assertEqual((self.model().bot_for().atb, self.model().bot_for().haste_turns), (0, 0))

    def test_large_and_small_frames_match_with_autonomous_actions_and_haste(self):
        large = self.model(rng=random.Random(123))
        small = self.model(rng=random.Random(123))
        for _ in range(16):
            large.update(1000)
            for _ in range(10000):
                if small.waiting_for_player or small.ended:break
                small.update(.013)
            self.assertEqual(self.snapshot(large), self.snapshot(small))
            command = 'overclock' if large.ready_actor == 'mira' and large.combatant('mira').mp >= 5 else 'guard'
            self.assertTrue(large.choose_action(command))
            self.assertTrue(small.choose_action(command))
        self.assertTrue(any(event.get('actor') == 'rivet' and event['type'] == 'impact'
                            for event in large.events))

    def test_fixed_timing_balance_benchmark_and_production_overclock_victory(self):
        catalog = json.loads(ACTION_PATH.read_text())
        # Hold Caelan's benchmark action times constant across all three groups
        # to compare Mira/Rivet economics independently of Caelan choreography.
        benchmark_actions = deepcopy(catalog)
        benchmark_actions['actions']['attack'].update(duration=.8, impact_at=.4)
        benchmark_actions['actions']['guard'].update(duration=.5, impact_at=.25)
        old_actions = deepcopy(benchmark_actions)
        old_actions['actions']['spear_thrust'] = dict(
            catalog['actions']['bolt_shot'], name='Spear Thrust', potency=1.5)
        old_guests = json.loads(GUEST_PATH.read_text())
        old_guests['guests']['mira']['attack'] = 'spear_thrust'
        enemies = json.loads(ENEMY_PATH.read_text())
        enemies['enemies']['ridgeback_tusker']['attributes'].update(
            hp=1000000, str=0, mag=0)

        def simulate(*, buff=False, real=False, **options):
            if not real:
                options['enemy_data'] = enemies
                options.setdefault('action_data', benchmark_actions)
            model = self.model(enemy_id='ridgeback_tusker', **options)
            history = []
            for tick in range(60000 if real else 9000):
                if model.waiting_for_player:
                    if model.ready_actor == model.telegraphed_target:command = 'guard'
                    elif (buff and model.ready_actor == 'mira'
                          and not model.active_bot().haste_turns
                          and model.combatant('mira').mp >= 5):command = 'overclock'
                    else:command = 'attack'
                    self.assertTrue(model.choose_action(command))
                model.update(.01)
                history.extend(model.drain_events())
                if model.ended:break
            damage = sum(event['damage'] for event in history
                         if event['type'] == 'impact' and event['actor'] in ('mira', 'rivet'))
            return model, history, damage, tick

        old_damage = simulate(action_data=old_actions, guest_data=old_guests,
                              bot_loadouts={})[2]
        plain_damage = simulate()[2]
        hasted_damage = simulate(buff=True)[2]
        self.assertGreaterEqual(plain_damage, old_damage*.9)
        self.assertLessEqual(plain_damage, old_damage*1.1)
        self.assertGreaterEqual(hasted_damage, plain_damage*1.03)
        self.assertLessEqual(hasted_damage, plain_damage*1.1)
        unbuffed, unbuffed_events, _, unbuffed_ticks = simulate(real=True)
        hasted, hasted_events, _, hasted_ticks = simulate(real=True, buff=True)
        for model, history in ((unbuffed, unbuffed_events), (hasted, hasted_events)):
            self.assertEqual(model.phase, 'victory')
            self.assertTrue(all(member.hp > 0 for member in model.party))
            charges = [event for event in history
                       if event['type'] == 'impact' and event['action'] == 'tusker_charge']
            self.assertTrue(charges)
            self.assertTrue(all(event['guarded'] for event in charges))
        self.assertLess(hasted_ticks, unbuffed_ticks)

    def test_bot_and_haste_data_reject_extra_fields_and_invalid_references(self):
        actions = load_actions()
        bots = json.loads(BOT_PATH.read_text())
        self.assertEqual(load_bots(actions, bots)['rivet']['attributes']['speed'], 8)
        for field, value in (('hp', 10), ('speed', True), ('speed', 256), ('str', 1000)):
            bad = deepcopy(bots)
            bad['bots']['rivet']['attributes'][field] = value
            with self.subTest(field=field):
                with self.assertRaises(ValueError):load_bots(actions, bad)
        for action_id in ('guard', 'aether_dart', 'missing'):
            bad = deepcopy(bots)
            bad['bots']['rivet']['ability_id'] = action_id
            bad['bots']['rivet']['ability_ids'] = [action_id]
            with self.subTest(action=action_id):
                with self.assertRaises(ValueError):load_bots(actions, bad)
        original = json.loads(ACTION_PATH.read_text())
        for field, value in (('turns', True), ('turns', 0), ('rate_multiplier', 1),
                             ('rate_multiplier', float('nan')), ('target', 'self'),
                             ('weapon_hits', 3), ('potency', 1)):
            bad = deepcopy(original)
            bad['actions']['overclock'][field] = value
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError):load_actions(bad)
        for bad in ({'mira': {'bot_id': 'rivet', 'ability_id': 'missing'}},
                    {'player': {'bot_id': 'rivet', 'ability_id': 'piston_jab'}},
                    {'mira': {'bot_id': 'rivet', 'ability_id': 'piston_jab', 'hp': 1}}):
            with self.subTest(loadout=bad):
                with self.assertRaises(ValueError):self.model(bot_loadouts=bad)
        bad = deepcopy(original)
        bad['actions']['piston_jab']['mp_cost'] = 1
        with self.assertRaises(ValueError):self.model(action_data=bad)


if __name__ == '__main__':unittest.main()
