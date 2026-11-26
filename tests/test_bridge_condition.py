"""Bridge state has explicit authority and preserves the legacy-layout origin."""
from dataclasses import FrozenInstanceError
from types import SimpleNamespace as NS
import unittest

from bridge_condition import (
    BridgeCondition, DEFAULT_REPAIR_FLAG, condition_for_game,
    resolve_condition, valid_snapshot,
)


class BridgeConditionTests(unittest.TestCase):
    def test_default_is_explicitly_destroyed_without_claiming_an_attack(self):
        condition = BridgeCondition()
        self.assertEqual(condition.to_dict(), {
            'version': 1, 'phase': 'destroyed', 'origin': 'explicit'})
        self.assertTrue(condition.destroyed)
        self.assertFalse(condition.passable)

    def test_all_legal_phase_origin_pairs_round_trip(self):
        pairs = [('intact', 'explicit'), ('destroyed', 'explicit'),
                 ('restored', 'explicit'), ('destroyed', 'legacy_layout'),
                 ('restored', 'legacy_repair')]
        for phase, origin in pairs:
            with self.subTest(phase=phase, origin=origin):
                condition = BridgeCondition(phase, origin)
                self.assertTrue(valid_snapshot(condition.to_dict()))
                self.assertEqual(resolve_condition(condition.to_dict()), condition)
                self.assertIs(resolve_condition(condition), condition)
                self.assertEqual(condition.passable, phase in ('intact', 'restored'))
                self.assertEqual(condition.destroyed, phase == 'destroyed')

    def test_constructor_rejects_invalid_combinations_and_types(self):
        for phase, origin in [('intact', 'legacy_layout'), ('restored', 'legacy_layout'),
                              ('intact', 'legacy_repair'), ('destroyed', 'legacy_repair'),
                              ('broken', 'explicit'), ('destroyed', 'attack'),
                              (None, 'explicit'), ('destroyed', True)]:
            with self.subTest(phase=phase, origin=origin):
                with self.assertRaises(ValueError):
                    BridgeCondition(phase, origin)

    def test_snapshot_validation_is_strict(self):
        valid = BridgeCondition().to_dict()
        malformed = [None, [], (), 1, True, 'destroyed', BridgeCondition(), {},
                     {'phase': 'destroyed', 'origin': 'explicit'},
                     dict(valid, extra=True), dict(valid, version=True),
                     dict(valid, version=1.0), dict(valid, version='1'),
                     dict(valid, version=2), dict(valid, phase=None),
                     dict(valid, phase=['destroyed']), dict(valid, origin=1),
                     dict(valid, phase='DESTROYED'), dict(valid, origin='attack'),
                     dict(valid, phase='intact', origin='legacy_layout'),
                     dict(valid, phase='destroyed', origin='legacy_repair')]
        for value in malformed:
            with self.subTest(value=value):
                self.assertFalse(valid_snapshot(value))

    def test_malformed_explicit_values_never_fall_back_to_repair_flags(self):
        for value in ({}, False, [], 'intact', {'version': 1, 'phase': 'intact'}):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    resolve_condition(value, flags={DEFAULT_REPAIR_FLAG})

    def test_condition_is_immutable_and_snapshot_is_independent(self):
        condition = BridgeCondition('intact')
        with self.assertRaises(FrozenInstanceError):
            condition.phase = 'destroyed'
        snapshot = condition.to_dict()
        snapshot['phase'] = 'destroyed'
        self.assertEqual(condition.phase, 'intact')
        self.assertEqual(hash(condition), hash(BridgeCondition('intact')))

    def test_legacy_fallback_keeps_live_layout_ruined_without_attack_inference(self):
        for flags in ((), None, {'SOME_OTHER_FLAG'}, {'FIRE_ATTACK_HAPPENED'}):
            with self.subTest(flags=flags):
                condition = resolve_condition(flags=flags)
                self.assertEqual(condition, BridgeCondition('destroyed', 'legacy_layout'))
                self.assertEqual(set(condition.to_dict()), {'version', 'phase', 'origin'})

    def test_legacy_repair_flag_resolves_restored_and_supports_custom_flag(self):
        self.assertEqual(resolve_condition(flags={DEFAULT_REPAIR_FLAG}),
                         BridgeCondition('restored', 'legacy_repair'))
        self.assertEqual(resolve_condition(flags={'CUSTOM'}, repair_flag='CUSTOM'),
                         BridgeCondition('restored', 'legacy_repair'))
        self.assertEqual(resolve_condition(flags={DEFAULT_REPAIR_FLAG}, repair_flag='CUSTOM'),
                         BridgeCondition('destroyed', 'legacy_layout'))
        self.assertEqual(resolve_condition(flags=DEFAULT_REPAIR_FLAG).phase, 'restored')
        self.assertEqual(resolve_condition(flags=DEFAULT_REPAIR_FLAG+'_OTHER').phase, 'destroyed')

    def test_explicit_conditions_do_not_read_or_obey_legacy_flags(self):
        class UnreadableFlags:
            def __contains__(self, key):
                raise AssertionError('Explicit condition must not inspect flags')
        for phase in ('intact', 'destroyed', 'restored'):
            condition = BridgeCondition(phase)
            with self.subTest(phase=phase):
                self.assertIs(resolve_condition(condition, flags=UnreadableFlags()), condition)
                self.assertEqual(resolve_condition(condition.to_dict(), flags=UnreadableFlags()),
                                 condition)
                self.assertEqual(resolve_condition(condition.to_dict(), flags={DEFAULT_REPAIR_FLAG}),
                                 condition)

    def test_game_owner_precedence_uses_existing_travel_then_world_then_flags(self):
        game = NS(overworld_travel=NS(bridge_condition=BridgeCondition('intact')),
                  world=NS(bridge_condition=BridgeCondition('destroyed')),
                  social=NS(flags={DEFAULT_REPAIR_FLAG}))
        self.assertEqual(condition_for_game(game), BridgeCondition('intact'))
        game.overworld_travel.bridge_condition = None
        self.assertEqual(condition_for_game(game), BridgeCondition('destroyed'))
        game.world.bridge_condition = None
        self.assertEqual(condition_for_game(game), BridgeCondition('restored', 'legacy_repair'))

    def test_world_snapshot_and_minimal_mocks_do_not_allocate_a_world(self):
        class GameWithoutAllocatedRegion:
            @property
            def overworld_world(self):
                raise AssertionError('Condition reader must not allocate the overworld')
        game = GameWithoutAllocatedRegion()
        self.assertEqual(condition_for_game(game), BridgeCondition('destroyed', 'legacy_layout'))
        game.world = NS(bridge_condition=BridgeCondition('restored').to_dict())
        self.assertEqual(condition_for_game(game), BridgeCondition('restored'))

    def test_game_legacy_flags_use_the_supplied_region_repair_flag(self):
        game = NS(social=NS(flags={'REGION_REPAIRED'}))
        region = {'bridge': {'repair_flag': 'REGION_REPAIRED'}}
        self.assertEqual(condition_for_game(game, region),
                         BridgeCondition('restored', 'legacy_repair'))
        self.assertEqual(condition_for_game(game), BridgeCondition('destroyed', 'legacy_layout'))

    def test_travel_owner_does_not_touch_lower_priority_world_or_flags(self):
        class GameWithTravelCondition:
            overworld_travel = NS(bridge_condition=BridgeCondition('intact'))

            @property
            def world(self):
                raise AssertionError('Travel condition already owns the answer')

            @property
            def social(self):
                raise AssertionError('Explicit condition must not inspect legacy flags')

        self.assertEqual(condition_for_game(GameWithTravelCondition()), BridgeCondition('intact'))

    def test_invalid_owner_does_not_hide_corruption_behind_a_lower_priority_owner(self):
        game = NS(overworld_travel=NS(bridge_condition={}),
                  world=NS(bridge_condition=BridgeCondition('intact')),
                  social=NS(flags={DEFAULT_REPAIR_FLAG}))
        with self.assertRaises(ValueError):
            condition_for_game(game)


if __name__ == '__main__':
    unittest.main()
