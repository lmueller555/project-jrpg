"""Real boss ATB, party-wide damage, fair windups and recovery arithmetic."""
from copy import deepcopy
import random
import unittest

from battle_model import BattleModel
from character_attributes import CharacterAttributes
from leveling import character_stats


CLAW, ROAR, GATHER, POUNCE, RECOVER = [
    'vespermaw_'+name for name in ('raking_claw', 'confluence_roar',
                                 'gather_resonance', 'ruinous_pounce', 'exhausted')]


class Variance:
    def __init__(self, values=(100,)):self.values, self.calls = values, 0
    def randint(self, low, high):
        assert (low, high) == (95, 105)
        result = self.values[self.calls % len(self.values)]
        self.calls += 1
        return result


def profiles(level=7, ids=('caelan', 'mira', 'lucan'), durable=False):
    members = []
    for identifier in ids:
        stats = character_stats(identifier, level)
        if durable:stats['hp'] = 9999
        members.append({'identifier': 'player' if identifier == 'caelan' else identifier,
                        'name': identifier.title(), 'attributes': stats,
                        'hp': stats['hp'], 'mp': stats['mp'],
                        'attack': 'bolt_shot' if identifier == 'mira' else 'attack'})
    return members


class VespermawLiveModelTests(unittest.TestCase):
    def model(self, **options):
        options.setdefault('party_members', profiles(durable=True))
        options.setdefault('rng', Variance())
        options.setdefault('weapon_equipped', True)
        options.setdefault('learned_abilities', ['aether_edge', 'aether_dart'])
        model = BattleModel.from_bestiary(CharacterAttributes(), 'vespermaw', 7, **options)
        model.enemy.hp = model.enemy.attributes['hp'] = 999999
        model.drain_events()
        return model

    def empty_gauges(self, model):
        for actor in (*model.party, *model.enemies):actor.atb = 0

    def finish(self, model):
        action = model.current_action
        model.update(action.duration-action.elapsed)
        self.assertTrue(action.resolved)
        return action

    def respond(self, model, command='guard'):
        self.empty_gauges(model)
        identifier = model.telegraphed_target
        member = model.combatant(identifier)
        member.atb = 1
        model.update(0)
        self.assertTrue(model.select_ready(identifier))
        self.assertTrue(model.choose_action(command))
        self.finish(model)

    def enemy_turn(self, model):
        self.empty_gauges(model)
        model.enemy.atb = 1
        model.update(0)
        self.assertEqual(model.current_action.actor, 'enemy')
        return self.finish(model)

    def prepare(self, model):
        model._enemy_action_index = 2
        return self.enemy_turn(model)

    def test_exact_cycle_free_roar_fallback_and_resource_cost(self):
        model = self.model()
        for remaining in (29, 0):
            model.enemy.mp = remaining
            model._enemy_action_index = 0
            actual = [self.enemy_turn(model).action for _ in range(3)]
            self.assertEqual(actual, [CLAW, ROAR if remaining else CLAW, GATHER])
            self.respond(model)
            self.assertEqual(self.enemy_turn(model).action, POUNCE)
            self.assertEqual(self.enemy_turn(model).action, RECOVER)
            self.assertEqual(model.enemy.mp, remaining-6 if remaining else 0)

    def test_roar_hits_each_living_member_with_independent_guard_and_variance(self):
        rng = Variance((95, 105))
        model = self.model(rng=rng)
        model.combatant('mira').hp = 0
        model.player.guarded = model.combatant('mira').guarded = True
        before = {member.identifier: member.hp for member in model.party}
        model._enemy_action_index = 1
        action = self.enemy_turn(model)
        impacts = [event for event in model.drain_events() if event['type'] == 'impact']
        self.assertEqual(action.targets, ('player', 'lucan'))
        self.assertEqual([event['target'] for event in impacts], ['player', 'lucan'])
        self.assertEqual(rng.calls, 2)
        self.assertTrue(impacts[0]['guarded'])
        self.assertFalse(impacts[1]['guarded'])
        self.assertFalse(model.player.guarded)
        self.assertTrue(model.combatant('mira').guarded)
        for event in impacts:
            self.assertEqual(before[event['target']]-model.combatant(event['target']).hp, event['damage'])
        self.assertEqual(action.damage, sum(event['damage'] for event in impacts))

    def test_roar_resolves_every_hit_before_defeat(self):
        model = self.model()
        for member in model.party:member.hp = 1
        model._enemy_action_index = 1
        self.enemy_turn(model)
        events = model.drain_events()
        self.assertEqual([event['target'] for event in events if event['type'] == 'impact'],
                         ['player', 'mira', 'lucan'])
        self.assertEqual(events[-1], {'type': 'result', 'outcome': 'defeat'})
        self.assertEqual(model.phase, 'defeat')

    def test_all_opponents_respects_actor_side(self):
        model = self.model()
        before = [member.hp for member in model.party]
        model._start_action('player', ROAR)
        action = self.finish(model)
        self.assertEqual(action.targets, ('enemy',))
        self.assertEqual([member.hp for member in model.party], before)
        self.assertEqual([event['target'] for event in model.drain_events()
                          if event['type'] == 'impact'], ['enemy'])

    def test_fast_enemy_waits_for_marked_members_real_command_without_gauge_boost(self):
        model = self.model()
        model._enemy_target_index = 1
        self.prepare(model)
        self.assertEqual(model.telegraphed_target, 'mira')
        self.empty_gauges(model)
        model.enemy.atb = 1
        model.enemy.attributes['speed'] = 255
        for member in model.party:member.attributes['speed'] = 0
        before = model.combatant('mira').hp
        model.update(1)
        self.assertEqual(model.phase, 'charging')
        self.assertAlmostEqual(model.combatant('mira').atb, .12)
        self.assertEqual(model.enemy.atb, 1)
        self.assertEqual(model.combatant('mira').hp, before)
        for _ in range(50):
            model.update(.25)
            if model.waiting_for_player:
                actor = model.ready_actor
                self.assertTrue(model.choose_action('guard' if actor == 'mira' else 'attack'))
            if model.current_action is not None and model.current_action.action == POUNCE:break
        else:self.fail('The marked character did not receive its command opportunity')
        self.assertTrue(model.combatant('mira').guarded)
        action = self.finish(model)
        self.assertEqual((action.action, action.target), (POUNCE, 'mira'))
        event = next(event for event in model.drain_events()
                     if event['type'] == 'impact' and event['action'] == POUNCE)
        self.assertTrue(event['guarded'])

    def test_retargeting_before_and_during_pounce_repeats_warning_and_response(self):
        for midair in (False, True):
            with self.subTest(midair=midair):
                model = self.model()
                self.prepare(model)
                old = model.telegraphed_target
                if midair:
                    self.respond(model)
                    self.empty_gauges(model);model.enemy.atb = 1;model.update(0)
                    self.assertEqual(model.current_action.action, POUNCE)
                model.combatant(old).hp = 0
                model.update(0)
                target = model.telegraphed_target
                self.assertNotEqual(target, old)
                self.assertEqual(model._enemy_states['enemy'].response_actions, 0)
                events = model.drain_events()
                self.assertTrue(any(event['type'] == 'telegraph' and event.get('retargeted')
                                    and event['target'] == target for event in events))
                self.assertIsNone(model.current_action)
                self.assertEqual(model.phase, 'charging')
                self.respond(model)
                self.assertEqual(self.enemy_turn(model).target, target)

    def test_recovery_spends_turn_and_ends_before_next_claw(self):
        model = self.model()
        self.prepare(model);self.respond(model);self.enemy_turn(model)
        self.assertEqual(model.enemy_recovery_states, {'enemy': 1.5})
        resources = (model.enemy.hp, model.enemy.mp)
        self.assertEqual(self.enemy_turn(model).action, RECOVER)
        self.assertEqual((model.enemy.hp, model.enemy.mp), resources)
        self.assertEqual(model.enemy_recovery_states, {'enemy': 1.5})
        self.empty_gauges(model);model.enemy.atb = 1;model.update(0)
        self.assertEqual(model.current_action.action, CLAW)
        self.assertEqual(model.enemy_recovery_states, {})
        events = model.drain_events()
        self.assertEqual(len([event for event in events if event['type'] == 'recovery_started']), 1)
        self.assertEqual(len([event for event in events if event['type'] == 'recovery_ended']), 1)

    def test_vulnerability_modifies_complete_physical_magical_rig_and_composite_hits_once(self):
        for actor, action, enchanted in (('player', 'attack', False),
                ('player', 'aether_dart', False), ('mira', 'bolt_shot', False),
                ('mira', 'charged_bolt', False), ('player', 'aether_edge', False),
                ('player', 'attack', True)):
            with self.subTest(actor=actor, action=action, enchanted=enchanted):
                hits = []
                for vulnerable in (False, True):
                    model = self.model()
                    model._enemy_states['enemy'].vulnerable = vulnerable
                    if enchanted:model.player.aether_edge_hits = 2
                    model._start_action(actor, action)
                    resolved = self.finish(model)
                    hits.append(resolved.damage)
                self.assertEqual(hits[1], hits[0]*3//2)
        model = self.model()
        model.player.attributes.update(str=999, mag=999)
        model._enemy_states['enemy'].vulnerable = True
        model._start_action('player', 'aether_edge')
        self.assertEqual(self.finish(model).damage, 9999)

    def test_flee_validation_cleanup_and_authored_solo_formation(self):
        model = self.model()
        self.empty_gauges(model);model.player.atb = 1;model.update(0)
        before = deepcopy((model.player.hp, model.player.mp, model.player.atb))
        self.assertIn('Cannot flee', model.action_reason('flee'))
        self.assertFalse(model.choose_action('flee'))
        self.assertEqual((model.player.hp, model.player.mp, model.player.atb), before)
        for outcome in ('victory', 'defeat', 'fled'):
            state = model._enemy_states['enemy']
            state.vulnerable = True;state.prepared_action = POUNCE;state.telegraphed_target = 'mira'
            state.response_actions = 1
            model._result(outcome)
            self.assertEqual(model.enemy_recovery_states, {})
            self.assertEqual(model.enemy_telegraphs, {})
            self.assertEqual(state.response_actions, 0)
        with self.assertRaisesRegex(ValueError, 'solo formation'):
            BattleModel.from_bestiary_group(CharacterAttributes(), [
                {'enemy_id': 'cave_bat', 'level': 2}, {'enemy_id': 'vespermaw', 'level': 7}])

    def test_actual_two_member_party_wins_at_six_and_seven_without_healing(self):
        for level, ids in ((6, ('caelan', 'mira')), (7, ('caelan', 'mira')),
                           (5, ('caelan', 'mira', 'lucan'))):
            for seed in range(10):
                with self.subTest(level=level, members=len(ids), seed=seed):
                    members = profiles(level, ids)
                    before = deepcopy(members)
                    model = BattleModel.from_bestiary(CharacterAttributes(), 'vespermaw', 7,
                        party_members=members, weapon_equipped=True, learned_abilities=['aether_edge'],
                        rng=random.Random(seed), initial_atb=True, initial_atb_seed=seed)
                    for _ in range(20000):
                        if model.waiting_for_player:
                            actor = model.ready_actor
                            if actor in model.enemy_telegraphs.values():command = 'guard'
                            elif actor == 'player' and model.active_player.mp >= 4:command = 'aether_edge'
                            else:command = 'attack'
                            self.assertTrue(model.choose_action(command))
                        model.update(.05);model.drain_events()
                        if model.ended:break
                    self.assertEqual(model.phase, 'victory')
                    self.assertEqual(members, before)
                    self.assertTrue(all(member.hp > 0 for member in model.party))

    def test_small_and_large_updates_preserve_windup_cycle_and_damage(self):
        def run(step):
            model = self.model()
            history, commands = [], 0
            for _ in range(200000):
                if model.waiting_for_player:
                    if commands == 40:break
                    actor = model.ready_actor
                    command = 'guard' if actor in model.enemy_telegraphs.values() else 'attack'
                    self.assertTrue(model.choose_action(command))
                    commands += 1
                model.update(step)
                history.extend({key: value for key, value in event.items() if key != 'frame_age'}
                               for event in model.drain_events())
            else:self.fail('Boss update comparison did not reach forty commands')
            state = model._enemy_states['enemy']
            return (history, [(actor.identifier, getattr(actor, 'hp', None),
                               getattr(actor, 'mp', None), round(actor.atb, 7))
                              for actor in (*model.party, *model.enemies)],
                    model.ready_actor, state.action_index, state.response_actions, state.vulnerable)
        self.assertEqual(run(.01), run(1000))
