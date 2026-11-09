"""Authored Caelan motion shares exact, deterministic battle action boundaries."""
from copy import deepcopy
import json
import math
import unittest

from battle_choreography import (CHOREOGRAPHY_PATH, action_timing,
                                 load_choreography, sample)
from battle_model import ACTION_PATH, ENEMY_PATH, BattleModel
from character_attributes import CharacterAttributes
from gear_state import REQUIRED_GEMS


class FixedVariance:
    def randint(self, low, high):
        assert (low, high) == (95, 105)
        return 100


class BattleChoreographyTests(unittest.TestCase):
    def model(self, **options):
        enemies = json.loads(ENEMY_PATH.read_text())
        enemies['enemies']['bat']['attributes'].update(hp=1000000, speed=0)
        options.setdefault('enemy_data', enemies)
        options.setdefault('learned_abilities', ['aether_edge', 'aether_dart'])
        options.setdefault('weapon_equipped', True)
        return BattleModel(CharacterAttributes(), rng=FixedVariance(), **options)

    def choose(self, model, action):
        model.player.atb = 1
        model.update(0)
        self.assertTrue(model.choose_action(action))
        return model.current_action

    def test_caelan_profiles_have_the_requested_contact_and_return_times(self):
        for identifier, expected in {'attack': (1.4, .72), 'aether_edge': (2., 1.),
                                     'aether_dart': (1.6, 1.1), 'guard': (.6, .2)}.items():
            with self.subTest(action=identifier):
                self.assertEqual(action_timing(identifier), expected)
                model = self.model()
                action = self.choose(model, identifier)
                self.assertEqual((action.duration, action.impact_at), expected)
                self.assertEqual(action.choreography, identifier)
                self.assertTrue(action.weapon_equipped)

    def test_melee_has_a_planted_contact_and_returns_home_before_results(self):
        for identifier in ('attack', 'aether_edge'):
            with self.subTest(action=identifier):
                duration, impact = action_timing(identifier)
                contact = sample(identifier, impact)
                self.assertEqual(contact.phase, 'strike')
                self.assertEqual(contact.approach, 1)
                self.assertEqual(contact.elevation, 0)
                self.assertEqual(contact.target_reaction, 1)
                self.assertEqual(sample(identifier, impact-.001).target_reaction, 0)
                end = sample(identifier, duration)
                self.assertEqual(end.phase, 'land')
                self.assertEqual((end.approach, end.camera_weight, end.target_reaction), (0, 0, 0))
                self.assertAlmostEqual(end.elevation, 0)
                model = self.model()
                model.enemy.hp = 1
                action = self.choose(model, identifier)
                gauges = [actor.atb for actor in (*model.party, *model.bots, model.enemy)]
                model.update(impact)
                self.assertEqual(model.enemy.hp, 0)
                self.assertEqual(model.phase, 'acting')
                model.update(duration-impact-.001)
                self.assertEqual(model.phase, 'acting')
                self.assertEqual([actor.atb for actor in (*model.party, *model.bots, model.enemy)], gauges)
                self.assertEqual(sum(event['type'] == 'impact' for event in model.events), 1)
                model.update(.001)
                self.assertEqual(model.phase, 'victory')
                self.assertEqual(model.last_action, action)

    def test_edge_focus_happens_at_home_and_existing_contact_frame_stays_aligned(self):
        focus = sample('aether_edge', .2)
        self.assertEqual((focus.phase, focus.pose, focus.approach), ('focus', 'focus_adjust', 0))
        self.assertEqual(sample('aether_edge', .6).phase, 'approach')
        contact = sample('aether_edge', 1.)
        self.assertEqual(contact.pose, 'aether_edge')
        self.assertAlmostEqual(contact.pose_ms, 500)

    def test_dart_prepares_releases_travels_and_recovers_on_the_model_clock(self):
        prepare = sample('aether_dart', .749)
        self.assertEqual(prepare.pose, 'cast_prepare')
        self.assertIsNone(prepare.projectile_progress)
        release = sample('aether_dart', .75)
        self.assertEqual(release.pose, 'cast_release')
        self.assertEqual(release.projectile_progress, 0)
        self.assertAlmostEqual(sample('aether_dart', .925).projectile_progress, .5)
        impact = sample('aether_dart', 1.1)
        self.assertEqual(impact.projectile_progress, 1)
        self.assertEqual(impact.target_reaction, 1)
        self.assertEqual(impact.pose, 'cast_recover')
        self.assertEqual(sample('aether_dart', 1.599).phase, 'recover')
        for time in (0, .75, 1.1, 1.6):
            self.assertEqual(sample('aether_dart', time).approach, 0)

    def test_guard_holds_a_stationary_brace_at_its_commit_boundary(self):
        model = self.model()
        action = self.choose(model, 'guard')
        self.assertFalse(model.player.guarded)
        model.update(action.impact_at)
        self.assertTrue(model.player.guarded)
        pose = sample('guard', action.impact_at)
        self.assertEqual((pose.phase, pose.pose, pose.approach), ('brace', 'guard_enter', 0))
        self.assertEqual(pose.elevation, 0)
        self.assertEqual(pose.target_reaction, 0)

    def test_authored_banks_play_whole_phases_and_slash_contact_stays_in_its_hit_frame(self):
        self.assertAlmostEqual(sample('aether_dart', .375).pose_ms, 280)
        self.assertAlmostEqual(sample('attack', .3).pose_ms, 270)
        slash_contact = sample('attack', .72)
        self.assertEqual(slash_contact.pose, 'slash')
        self.assertGreaterEqual(slash_contact.pose_ms, 90)
        self.assertLess(slash_contact.pose_ms, 180)
        self.assertEqual(sample('guard', .5).pose, 'guard_enter')

    def test_weapon_snapshot_selects_the_bank_without_changing_unarmed_motion(self):
        model = self.model(weapon_equipped=False)
        action = self.choose(model, 'attack')
        self.assertFalse(action.weapon_equipped)
        self.assertEqual((action.duration, action.impact_at), (1.4, .72))
        model.weapon_equipped = True
        self.assertFalse(action.weapon_equipped)
        armed = sample('attack', .72)
        unarmed = sample('attack', .72, armed=False)
        self.assertTrue(armed.armed)
        self.assertFalse(unarmed.armed)
        self.assertEqual((armed.pose, armed.approach, armed.pose_ms),
                         (unarmed.pose, unarmed.approach, unarmed.pose_ms))

    def test_shared_enemy_guest_and_bot_actions_retain_catalog_timings(self):
        model = self.model(guest_id='mira')
        catalog = json.loads(ACTION_PATH.read_text())['actions']
        for actor, identifier in (('enemy', 'attack'), ('mira', 'guard'),
                                  (model.bots[0].identifier, model.bots[0].ability_id)):
            with self.subTest(actor=actor, action=identifier):
                model._start_action(actor, identifier)
                action = model.current_action
                self.assertEqual((action.duration, action.impact_at),
                                 (catalog[identifier]['duration'], catalog[identifier]['impact_at']))
                self.assertIsNone(action.choreography)

    def test_custom_action_timings_are_not_replaced_by_visual_profiles(self):
        data = json.loads(ACTION_PATH.read_text())
        data['actions']['attack'].update(duration=.8, impact_at=.25)
        model = self.model(action_data=data)
        action = self.choose(model, 'attack')
        self.assertEqual((action.duration, action.impact_at), (.8, .25))
        self.assertIsNone(action.choreography)
        self.assertEqual(model.actions['attack'], data['actions']['attack'])

    def test_lesson_keeps_failed_focus_at_half_a_second_and_discovery_at_one_second(self):
        model = BattleModel(CharacterAttributes(), enemy_id='ridgeback_tusker',
                            guest_id='mira', weapon_equipped=True,
                            spellblade_tutorial=True, rng=FixedVariance())
        model.update(1000)
        self.assertTrue(model.choose_action('guard'))
        model.update(1000)
        self.assertEqual(model.spellblade_stage, 'first_edge')
        self.assertTrue(model.choose_action('aqua_edge'))
        failure = model.current_action
        self.assertEqual((failure.duration, failure.impact_at), (.9, .5))
        self.assertIsNone(failure.choreography)
        model.update(.499)
        self.assertEqual(model.spellblade_stage, 'first_edge')
        model.update(.001)
        self.assertEqual(model.spellblade_stage, 'second_edge')
        self.assertFalse(model.aether_edge_discovered)
        model.update(.4)
        model.update(0)
        self.assertEqual(model.current_action.action, 'aether_edge')
        self.assertEqual(model.current_action.choreography, 'aether_edge')
        model.update(.999)
        self.assertFalse(model.aether_edge_discovered)
        model.update(.001)
        self.assertTrue(model.aether_edge_discovered)
        self.assertEqual(sum(event['type'] == 'spellblade_discovered'
                             for event in model.events), 1)

    def test_sampling_can_scrub_without_state_and_clamps_outside_the_action(self):
        midpoint = sample('attack', .32)
        sample('attack', 1.4)
        self.assertEqual(sample('attack', .32), midpoint)
        self.assertEqual(sample('attack', -10), sample('attack', 0))
        self.assertEqual(sample('attack', 100), sample('attack', 1.4))
        for invalid in (math.inf, math.nan):
            with self.assertRaises(ValueError):sample('attack', invalid)
        with self.assertRaises(TypeError):sample('attack', True)
        with self.assertRaises(ValueError):sample('unknown', 0)

    def test_impact_frame_age_places_reactions_at_the_same_absolute_time(self):
        large, small = self.model(), self.model()
        action = self.choose(large, 'attack')
        self.choose(small, 'attack')
        large.update(.9)
        impact = next(event for event in large.events if event['type'] == 'impact')
        self.assertAlmostEqual(impact['frame_age'], .9-action.impact_at)
        small_impact_time = None
        for index in range(90):
            small.update(.01)
            for event in small.drain_events():
                if event['type'] == 'impact':
                    small_impact_time = (index+1)*.01-event['frame_age']
        self.assertAlmostEqual(.9-impact['frame_age'], small_impact_time)
        self.assertEqual(large.enemy.hp, small.enemy.hp)
        large.update(.1)
        self.assertAlmostEqual(impact['frame_age'], .9-action.impact_at)

    def test_impact_frame_age_includes_unused_time_after_victory(self):
        model = self.model()
        model.enemy.hp = 1
        action = self.choose(model, 'attack')
        model.update(5)
        impact = next(event for event in model.events if event['type'] == 'impact')
        self.assertEqual(model.phase, 'victory')
        self.assertAlmostEqual(impact['frame_age'], 5-action.impact_at)

    def test_authored_catalog_rejects_gaps_and_failure_to_return_home(self):
        original = json.loads(CHOREOGRAPHY_PATH.read_text())
        for mutate in (lambda action: action['phases'][1].update(start=.15),
                       lambda action: action['phases'][-1].update(approach=[0, 1]),
                       lambda action: action.update(impact_at=0),
                       lambda action: action.update(release_at=action['impact_at'])):
            broken = deepcopy(original)
            mutate(broken['actions']['attack'])
            with self.assertRaises(ValueError):load_choreography(broken)
        parsed = load_choreography(original)
        parsed['attack']['duration'] = 9
        self.assertEqual(original['actions']['attack']['duration'], 1.4)


if __name__ == '__main__':unittest.main()
