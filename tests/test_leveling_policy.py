"""Combat-only XP eligibility and level growth without resource recovery."""
from copy import deepcopy
import unittest

from character_attributes import ATTRIBUTE_CAPS, MAX_ATTRIBUTE_VALUE, CharacterAttributes
from leveling import (CharacterLevel, character_ids, character_stats,
                      combat_xp_allocations, monster_xp, total_xp_for_level)


class CombatXpAllocationTests(unittest.TestCase):
    def test_each_living_combatant_receives_the_full_monster_sum(self):
        hp = {'caelan': 1, 'mira': 0, 'lucan': 90, 'rhea': 100, 'edran': 160}
        before = dict(hp)
        xp = sum(monster_xp(1) for _ in range(3))
        allocations = combat_xp_allocations(xp, ('caelan', 'mira', 'lucan'), hp)
        self.assertEqual(allocations, {'caelan': 180, 'mira': 0, 'lucan': 180})
        self.assertEqual(hp, before)
        self.assertNotIn('rhea', allocations)
        self.assertNotIn('edran', allocations)

    def test_party_size_does_not_divide_rewards_and_ko_receives_zero(self):
        hp = {'caelan': 140, 'mira': 150, 'lucan': 170}
        for active in (('caelan',), ('caelan', 'mira'), ('caelan', 'mira', 'lucan')):
            with self.subTest(active=active):
                self.assertEqual(combat_xp_allocations(600, active, hp),
                                 dict.fromkeys(active, 600))
        self.assertEqual(combat_xp_allocations(600, ('caelan',), {'caelan': 0}),
                         {'caelan': 0})
        self.assertEqual(combat_xp_allocations(0, ('caelan',), hp), {'caelan': 0})

    def test_invalid_snapshots_fail_without_mutating_inputs(self):
        hp = {'caelan': 140, 'mira': 150}
        cases = [(-1, ('caelan',), hp), (True, ('caelan',), hp),
                 (1.5, ('caelan',), hp), (60, (), hp),
                 (60, ('caelan', 'caelan'), hp), (60, ('player',), hp),
                 (60, ('caelan', []), hp), (60, ('rhea',), hp),
                 (60, ('caelan', 'mira', 'lucan', 'rhea'), hp),
                 (60, ('caelan',), None), (60, ('caelan',), {'caelan': True}),
                 (60, ('caelan',), {'caelan': -1}),
                 (60, ('caelan',), {'caelan': 10000}),
                 (60, ('caelan',), {'caelan': 140, 'rivet': 1})]
        for amount, active, resources in cases:
            before = deepcopy(resources)
            with self.subTest(amount=amount, active=active, resources=resources):
                with self.assertRaises((TypeError, ValueError)):
                    combat_xp_allocations(amount, active, resources)
                self.assertEqual(resources, before)


class LevelGrowthResourceTests(unittest.TestCase):
    def test_level_award_gains_preserve_depleted_resources_for_all_characters(self):
        for identifier in character_ids():
            catalog = deepcopy(CharacterAttributes().catalog)
            catalog['characters'] = {identifier: {
                'name': identifier.title(), 'attributes': character_stats(identifier, 1)}}
            for hp, mp in ((0, 0), (1, 0), (17, 7)):
                with self.subTest(character=identifier, hp=hp, mp=mp):
                    attributes = CharacterAttributes(identifier, catalog)
                    self.assertTrue(attributes.set_current(hp=hp, mp=mp))
                    level = CharacterLevel(identifier)
                    award = level.award_xp(total_xp_for_level(25))
                    self.assertTrue(attributes.apply_growth(dict(award.stat_gains)))
                    self.assertEqual(attributes.to_dict()['attributes'],
                                     character_stats(identifier, 25))
                    self.assertEqual((attributes.current_hp, attributes.current_mp), (hp, mp))
                    saved = attributes.to_dict()
                    restored = CharacterAttributes(identifier, catalog)
                    self.assertTrue(restored.restore(saved))
                    self.assertEqual(restored.to_dict(), saved)

    def test_growth_preserves_modifier_ownership_and_stops_at_base_caps(self):
        attributes = CharacterAttributes()
        self.assertTrue(attributes.set_modifiers('equipment', {'hp': 100, 'str': 25}))
        self.assertTrue(attributes.set_current(hp=220, mp=3))
        self.assertTrue(attributes.apply_growth({'hp': 30, 'mp': 5, 'str': 10}))
        self.assertEqual((attributes.base_value('hp'), attributes.value('hp')), (170, 270))
        self.assertEqual((attributes.base_value('str'), attributes.value('str')), (20, 45))
        self.assertEqual((attributes.current_hp, attributes.current_mp), (220, 3))
        self.assertTrue(attributes.apply_growth(dict.fromkeys(ATTRIBUTE_CAPS, 20000)))
        self.assertEqual(attributes.to_dict()['attributes'], ATTRIBUTE_CAPS)
        self.assertEqual((attributes.current_hp, attributes.current_mp), (220, 3))
        self.assertTrue(attributes.set_modifiers('equipment', {}))
        self.assertEqual(attributes.value('str'), 999)

    def test_invalid_growth_and_raw_overflow_are_atomic(self):
        attributes = CharacterAttributes()
        self.assertTrue(attributes.set_current(hp=19, mp=2))
        self.assertTrue(attributes.set_modifiers('equipment', {'str': MAX_ATTRIBUTE_VALUE-10}))
        before = attributes.to_dict(), deepcopy(attributes._modifiers)
        for gains in (None, [], {'hp': -1}, {'mp': True}, {'str': 1.5},
                      {'unknown': 1}, {'hp': MAX_ATTRIBUTE_VALUE+1}, {'str': 1}):
            with self.subTest(gains=gains):
                self.assertFalse(attributes.apply_growth(gains))
                self.assertEqual((attributes.to_dict(), attributes._modifiers), before)


if __name__ == '__main__':
    unittest.main()
