"""Gear focus eligibility and a global charging clock keep battle boundaries."""
from copy import deepcopy
import json
import random
import unittest

from battle_model import ACTION_PATH, ENEMY_PATH, BattleModel, ELEMENTAL_EDGE_ATTEMPTS
from character_attributes import CharacterAttributes
from gear_state import DEFAULT_GEM, GEM_COLORS, GEM_NAMES, GEM_ORDER, REQUIRED_GEMS, valid_gem
from test_aether_edge_battle_model import FixedVariance


class GearBattleModelTests(unittest.TestCase):
    def model(self, **options):
        enemies = json.loads(ENEMY_PATH.read_text())
        enemies['enemies']['bat']['attributes'].update(hp=1000000, str=0, mag=0, speed=0)
        options.setdefault('enemy_data', enemies)
        options.setdefault('weapon_equipped', True)
        options.setdefault('rng', FixedVariance())
        return BattleModel(CharacterAttributes(), **options)

    def snapshot(self, model):
        events = [{key: value for key, value in event.items() if key != 'frame_age'}
                  for event in model.events]
        actors = [(actor.identifier, actor.hp, actor.mp, round(actor.atb, 9))
                  for actor in (*model.party, model.enemy)]
        bots = [(bot.identifier, round(bot.atb, 9), bot.haste_turns)
                for bot in model.bots]
        action = model.current_action
        active = (action.actor, action.action, round(action.elapsed, 9),
                  action.damage, action.resolved, action.active_gem) if action else None
        return (model.phase, model.active_gem, model.learned_abilities,
                actors, bots, active, deepcopy(events))

    def ready(self, model, actor='player'):
        model.update(1000)
        self.assertTrue(model.waiting_for_player)
        self.assertEqual(model.ready_actor, actor)

    def implemented_edges(self):
        # A later quest must supply its authored action as well as an unlock.
        # This controlled fixture exercises eligibility without changing the
        # shipped lesson-only records or inventing a production damage balance.
        catalog = json.loads(ACTION_PATH.read_text())
        for identifier in REQUIRED_GEMS:
            catalog['actions'][identifier] = dict(catalog['actions']['aether_edge'],
                                                 name=identifier.replace('_', ' ').title())
        return catalog

    def test_canonical_focus_defaults_and_validation(self):
        self.assertEqual(GEM_ORDER, ('nature', 'water', 'fire', 'ice'))
        self.assertEqual(set(GEM_NAMES), set(GEM_ORDER))
        self.assertEqual(set(GEM_COLORS), set(GEM_ORDER))
        model = self.model()
        self.assertEqual(model.active_gem, DEFAULT_GEM)
        self.assertEqual(model.active_gem, 'water')
        for gem in GEM_ORDER:
            self.assertTrue(valid_gem(gem))
            self.assertTrue(model.set_active_gem(gem))
            self.assertEqual(model.active_gem, gem)
        for value in (None, False, 0, [], {}, 'Water', 'blue', ''):
            with self.subTest(value=value):
                before = self.snapshot(model)
                self.assertFalse(valid_gem(value))
                self.assertFalse(model.set_active_gem(value))
                self.assertEqual(self.snapshot(model), before)
                with self.assertRaises(ValueError):self.model(active_gem=value)

    def test_selecting_gems_never_changes_resources_turns_or_unlocks(self):
        model = self.model(learned_abilities=['aether_edge'])
        self.ready(model)
        before = self.snapshot(model)
        for gem in GEM_ORDER:
            self.assertTrue(model.set_active_gem(gem))
            after = self.snapshot(model)
            self.assertEqual(after[:1]+after[2:], before[:1]+before[2:])
            self.assertEqual(model.skill_actions(), ['aether_edge'])
        self.assertEqual(model.actions['nature_edge']['kind'], 'failed_edge')
        self.assertEqual(model.actions['ice_edge']['kind'], 'spellblade')
        shipped = self.model(learned_abilities=list(REQUIRED_GEMS))
        self.assertEqual(shipped.skill_actions(), ['aqua_edge', 'flame_edge', 'ice_edge'])
        self.assertFalse(shipped.choose_action('ice_edge'))

    def test_selector_locks_during_caelan_action_unarmed_ko_and_results(self):
        model = self.model(learned_abilities=['aether_edge'])
        self.ready(model)
        self.assertTrue(model.choose_action('aether_edge'))
        self.assertEqual(model.current_action.active_gem, 'water')
        self.assertFalse(model.gear_available)
        self.assertTrue(model.gear_busy)
        before = self.snapshot(model)
        self.assertFalse(model.set_active_gem('fire'))
        self.assertFalse(model.set_active_gem('water'))
        self.assertEqual(self.snapshot(model), before)
        model.update(model.current_action.duration)
        self.assertTrue(model.gear_available)
        for option in ({'weapon_equipped': False}, {}):
            locked = self.model(**option)
            if not option:locked.player.hp = 0
            self.assertFalse(locked.gear_available)
            self.assertFalse(locked.set_active_gem('nature'))
        for outcome in ('victory', 'defeat', 'fled'):
            locked = self.model()
            locked._result(outcome)
            before = self.snapshot(locked)
            self.assertFalse(locked.set_active_gem('fire'))
            self.assertEqual(self.snapshot(locked), before)

    def test_settling_blocks_caelan_commands_but_can_commit_and_does_not_block_mira(self):
        model = self.model(guest_id='mira', learned_abilities=['aether_edge'])
        model.player.atb = model.combatant('mira').atb = 1
        model.update(0)
        model.gear_settling = True
        self.assertTrue(model.gear_busy)
        for command in ('attack', 'aether_edge', 'guard', 'flee'):
            self.assertEqual(model.action_reason(command), 'The gear is settling.')
            self.assertFalse(model.choose_action(command))
        self.assertEqual(model.command_reason('skills'), 'The gear is settling.')
        self.assertTrue(model.set_active_gem('ice'))
        self.assertTrue(model.gear_settling)
        self.assertTrue(model.choose_action('attack', actor_id='mira'))
        self.assertTrue(model.set_active_gem('fire'))
        self.assertIsNone(model.current_action.active_gem)
        model.update(model.current_action.duration)
        model.gear_settling = False
        self.assertTrue(model.choose_action('aether_edge', actor_id='player'))
        self.assertEqual(model.current_action.active_gem, 'fire')

    def test_enemy_and_mira_actions_do_not_lock_caelans_selector(self):
        for actor in ('enemy', 'mira'):
            with self.subTest(actor=actor):
                model = self.model(guest_id='mira')
                model.combatant(actor).atb = 1
                model.update(0)
                if actor == 'mira':self.assertTrue(model.choose_action('attack'))
                self.assertEqual(model.current_action.actor, actor)
                self.assertTrue(model.gear_available)
                self.assertTrue(model.set_active_gem('nature'))
                self.assertIsNone(model.current_action.active_gem)

    def test_implemented_elements_require_both_unlock_and_matching_settled_gem(self):
        for identifier, required in REQUIRED_GEMS.items():
            for gem in GEM_ORDER:
                for learned in (False, True):
                    with self.subTest(action=identifier, gem=gem, learned=learned):
                        model = self.model(action_data=self.implemented_edges(), active_gem=gem,
                                           learned_abilities=[identifier] if learned else [])
                        self.ready(model)
                        before = self.snapshot(model)
                        permitted = learned and gem == required
                        self.assertEqual(model.choose_action(identifier), permitted)
                        if not permitted:
                            self.assertEqual(self.snapshot(model), before)
                            if learned:self.assertEqual(model.action_reason(identifier),
                                                        'Requires the '+GEM_NAMES[required]+' gem.')
                        else:
                            self.assertEqual(model.current_action.active_gem, gem)
                            self.assertEqual(model.player.mp, 26)
                            self.assertEqual(model.player.atb, 0)
                            model.update(model.current_action.impact_at)
                            self.assertGreater(model.current_action.damage, 0)
                            self.assertIsNone(model.spellblade_stage)
                            self.assertFalse(model.aether_edge_discovered)

    def test_element_weapon_mp_and_readiness_checks_still_apply(self):
        for armed, mp, ready, reason in ((False, 30, True, 'Requires a weapon.'),
                                         (True, 3, True, 'Not enough MP.'),
                                         (True, 30, False, 'Caelan is not ready.')):
            model = self.model(action_data=self.implemented_edges(), active_gem='nature',
                               learned_abilities=['nature_edge'], weapon_equipped=armed)
            model.player.mp = mp
            if ready:self.ready(model)
            before = self.snapshot(model)
            self.assertEqual(model.action_reason('nature_edge'), reason)
            self.assertFalse(model.choose_action('nature_edge'))
            self.assertEqual(self.snapshot(model), before)

    def test_aether_edge_remains_non_elemental_for_every_gem(self):
        damages = []
        for gem in GEM_ORDER:
            model = self.model(active_gem=gem, learned_abilities=['aether_edge'])
            self.ready(model)
            self.assertEqual(model.action_reason('aether_edge'), '')
            self.assertTrue(model.choose_action('aether_edge'))
            model.update(model.current_action.impact_at)
            damages.append(model.current_action.damage)
        self.assertEqual(len(set(damages)), 1)

    def test_blue_only_tutorial_attempt_and_automatic_aether_require_one_focus(self):
        for initial in GEM_ORDER:
            with self.subTest(initial=initial):
                model = self.model(enemy_id='ridgeback_tusker', guest_id='mira',
                                   spellblade_tutorial=True, active_gem=initial)
                self.ready(model)
                self.assertEqual(model.spellblade_stage, 'guard')
                self.assertTrue(model.choose_action('guard'))
                self.ready(model)
                self.assertEqual(model.skill_actions(), ['aqua_edge'])
                if initial != 'water':
                    self.assertFalse(model.choose_action('aqua_edge'))
                self.assertTrue(model.set_active_gem('water'))
                self.assertFalse(model.set_active_gem('fire'))
                self.assertTrue(model.choose_action('aqua_edge'))
                model.update(model.current_action.duration)
                self.assertEqual(model.current_action.action, 'aether_edge')
                self.assertEqual(model.current_action.active_gem, 'water')
                model.update(model.current_action.impact_at)
                self.assertEqual(model.spellblade_stage, 'complete')
                self.assertEqual(model.learned_abilities, frozenset(['aether_edge']))
                self.assertTrue(model.aether_edge_discovered)

    def test_global_multiplier_changes_every_character_and_enemy_gauge(self):
        model = self.model(guest_id='mira')
        for actor in (*model.party, model.enemy):actor.atb = .21
        initial = {actor.identifier: actor.atb for actor in (*model.party, model.enemy)}
        model.update(.4, atb_multiplier=.2)
        for actor in (*model.party, model.enemy):
            self.assertAlmostEqual(actor.atb, initial[actor.identifier]+model.atb_rate(actor)*.4*.2)
        self.assertEqual(model.bots, ())

    def test_scaled_exact_ready_boundary_and_unscaled_ready_wait(self):
        for multiplier in (.2, 1., 3.):
            model = self.model()
            boundary = 1/model.atb_rate(model.player)/multiplier
            model.update(boundary-.001, atb_multiplier=multiplier)
            self.assertEqual(model.phase, 'charging')
            model.update(.001, atb_multiplier=multiplier)
            self.assertEqual(model.ready_actor, 'player')
            self.assertEqual(model.player.atb, 1)
            before = self.snapshot(model)
            model.update(10000, atb_multiplier=7)
            self.assertEqual(self.snapshot(model), before)

    def test_multiplier_never_scales_action_impact_or_completion(self):
        for multiplier in (0, .2, 3):
            model = self.model(guest_id='mira', learned_abilities=['aether_edge'])
            model.player.atb = 1
            model.update(0)
            self.assertTrue(model.choose_action('aether_edge'))
            gauges = [actor.atb for actor in (*model.party, *model.bots, model.enemy)]
            action = model.current_action
            model.update(action.impact_at-.001, atb_multiplier=multiplier)
            self.assertFalse(model.current_action.resolved)
            model.update(.001, atb_multiplier=multiplier)
            self.assertTrue(model.current_action.resolved)
            self.assertEqual(model.current_action.elapsed, action.impact_at)
            self.assertEqual([actor.atb for actor in (*model.party, *model.bots, model.enemy)], gauges)
            model.update(action.duration-action.impact_at, atb_multiplier=multiplier)
            self.assertEqual(model.phase, 'charging')
            self.assertEqual(model.last_action.elapsed, action.duration)
            model.update(.1, atb_multiplier=multiplier)
            self.assertAlmostEqual(model.player.atb, model.atb_rate(model.player)*.1*multiplier)

    def test_zero_multiplier_freezes_charging_and_keeps_full_gauge_priority(self):
        model = self.model(guest_id='mira')
        before = self.snapshot(model)
        model.update(10000, atb_multiplier=0)
        self.assertEqual(self.snapshot(model), before)
        for actor in (*model.party, *model.bots, model.enemy):actor.atb = 1
        model.update(0, atb_multiplier=0)
        self.assertEqual(model.ready_actor, 'player')
        model.choose_action('guard');model.update(model.current_action.duration, atb_multiplier=0)
        self.assertEqual(model.ready_actor, 'mira')
        model.choose_action('guard');model.update(model.current_action.duration, atb_multiplier=0)
        self.assertEqual(model.current_action.actor, 'enemy')

    def test_multiplier_validation_is_atomic(self):
        model = self.model(guest_id='mira')
        model.combatant('mira').hp = 0  # Would cause an event if sync ran first.
        before = self.snapshot(model)
        for value in (False, True, None, '1', -1, float('nan'), float('inf')):
            with self.subTest(value=value):
                with self.assertRaises((TypeError, ValueError)):
                    model.update(.1, atb_multiplier=value)
                self.assertEqual(self.snapshot(model), before)

    def test_large_and_small_frames_match_with_slow_party_and_enemy_boundaries(self):
        large = self.model(guest_id='mira', rng=random.Random(47))
        small = self.model(guest_id='mira', rng=random.Random(47))
        for turn in range(12):
            multiplier = (.2, 1., 2.)[turn % 3]
            large.update(1000, atb_multiplier=multiplier)
            for _ in range(10000):
                if small.waiting_for_player or small.ended:break
                small.update(.013, atb_multiplier=multiplier)
            self.assertEqual(self.snapshot(large), self.snapshot(small))
            self.assertTrue(large.choose_action('guard'))
            self.assertTrue(small.choose_action('guard'))
        self.assertTrue(any(event['type'] == 'impact' and event['actor'] == 'enemy'
                            for event in large.events))


if __name__ == '__main__':unittest.main()
