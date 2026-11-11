"""Live EXP plans preserve resources, migration baselines and reward boundaries."""
from copy import deepcopy
import json
import unittest

from character_attributes import ATTRIBUTE_CAPS, ATTRIBUTE_IDS, CharacterAttributes
from character_progression import CharacterProgression
from leveling import (CharacterLevel, MAX_TOTAL_XP, character_ids, character_stats,
                      total_xp_for_level)
from party_state import PartyState


class CharacterProgressionTests(unittest.TestCase):
    def setUp(self):
        self.party = PartyState(CharacterAttributes())
        self.progression = CharacterProgression(self.party)

    def state(self):
        return self.progression.to_dict(), self.party.to_dict()

    def plan(self, amount=600, active=('caelan', 'mira', 'lucan')):
        return self.progression.preview(amount, active, dict.fromkeys(active, 1))

    def test_construction_and_old_save_migration_preserve_all_saved_values(self):
        attributes = self.party.characters['mira']
        self.assertEqual(attributes.base_value('hp'), 150)  # Balanced guest.
        self.assertTrue(attributes.apply_growth({'str': 17, 'hp': 31}))
        self.assertTrue(attributes.set_modifiers('equipment', {'def': 8}))
        self.assertTrue(attributes.set_current(hp=0, mp=3))
        before = deepcopy(self.party.to_dict())
        modifiers = deepcopy(attributes._modifiers)
        progression = CharacterProgression(self.party)
        progression.records['mira'].award_xp(600)
        self.assertTrue(progression.restore())
        self.assertEqual(self.party.to_dict(), before)
        self.assertEqual(attributes._modifiers, modifiers)
        self.assertTrue(all(progression.level(identifier) == 1 for identifier in character_ids()))
        self.assertTrue(CharacterProgression.valid_journey({'party': before}))

    def test_legacy_mira_retune_preserves_growth_modifiers_injury_and_is_idempotent(self):
        for level in (1, 7, 100):
            for injured in (False, True):
                with self.subTest(level=level, injured=injured):
                    record = CharacterLevel('mira', total_xp_for_level(level))
                    self.progression.records['mira'] = record
                    natural = character_stats('mira', level)
                    start = character_stats('mira', 1)
                    old = dict(zip(ATTRIBUTE_IDS, (300, 30, 20, 12, 12, 18, 14, 12, 16, 12, 10)))
                    attributes = self.party.characters['mira']
                    attributes._attributes = {key: old[key]+natural[key]-start[key] for key in ATTRIBUTE_IDS}
                    attributes.set_modifiers('equipment', {'def': 8})
                    attributes.set_current(hp=attributes.value('hp')//2 if injured else 0, mp=3)
                    xp = record.total_xp
                    self.assertTrue(self.progression.retune_legacy_mira())
                    self.assertEqual(attributes.to_dict()['attributes'], natural)
                    self.assertEqual(attributes.value('def')-attributes.base_value('def'), 8)
                    self.assertEqual(attributes.current_mp, 3)
                    self.assertEqual(attributes.current_hp > 0, injured)
                    self.assertEqual(record.total_xp, xp)
                    before = attributes.to_dict()
                    self.assertFalse(self.progression.retune_legacy_mira())
                    self.assertEqual(attributes.to_dict(), before)
        attributes.apply_growth({'str': 17})
        before = attributes.to_dict()
        self.assertFalse(self.progression.retune_legacy_mira())
        self.assertEqual(attributes.to_dict(), before)

    def test_genuinely_new_journey_uses_approved_starting_profiles_for_all_five(self):
        identities = {key: value for key, value in self.party.characters.items()}
        self.party.characters['mira'].set_modifiers('old_effect', {'def': 8})
        self.progression.records['caelan'].award_xp(600)
        self.assertTrue(self.progression.initialize_new_game())
        for identifier in character_ids():
            with self.subTest(character=identifier):
                attributes = self.party.characters[identifier]
                expected = character_stats(identifier, 1)
                self.assertIs(attributes, identities[identifier])
                self.assertEqual(attributes.to_dict()['attributes'], expected)
                self.assertEqual((attributes.current_hp, attributes.current_mp),
                                 (expected['hp'], expected['mp']))
                self.assertEqual(attributes._modifiers, {})
                self.assertEqual(self.progression.level(identifier), 1)

    def test_preview_is_pure_gives_full_xp_to_survivors_and_keeps_ko_explanation(self):
        self.party.recruit('mira');self.party.recruit('lucan');self.party.recruit('rhea')
        before = self.state()
        end_hp = {'caelan': 0, 'mira': 1, 'lucan': 25, 'rhea': 100}
        plan = self.progression.preview(180, self.party.active_ids, end_hp)
        self.assertTrue(CharacterProgression.valid_plan(plan))
        self.assertEqual(plan['active_ids'], ['caelan', 'mira', 'lucan'])
        self.assertEqual(plan['end_hp'], {'caelan': 0, 'mira': 1, 'lucan': 25})
        self.assertEqual({key: value['requested_xp'] for key, value in plan['characters'].items()},
                         {'caelan': 0, 'mira': 180, 'lucan': 180})
        self.assertNotIn('rhea', plan['characters'])
        self.assertEqual(self.state(), before)
        # Eligibility uses the actual end snapshot, not this living save state.
        self.assertGreater(self.party.characters['caelan'].current_hp, 0)
        self.assertEqual(plan['characters']['caelan']['old_total_xp'],
                         plan['characters']['caelan']['new_total_xp'])

    def test_multilevel_awards_apply_approved_growth_without_restoring_any_resource(self):
        self.progression.initialize_new_game()
        for identifier in character_ids():
            self.party.characters[identifier].set_current(hp=17, mp=3)
        for active in (('caelan', 'mira', 'lucan'), ('rhea', 'edran')):
            amount = total_xp_for_level(10)+25
            plan = self.progression.preview(amount, active, dict.fromkeys(active, 1))
            self.assertTrue(self.progression.matches_plan(plan))
            self.assertTrue(self.progression.apply(plan))
            self.assertTrue(self.progression.matches_plan(plan, after=True))
            self.assertFalse(self.progression.apply(plan))
            for identifier in active:
                with self.subTest(character=identifier):
                    attributes = self.party.characters[identifier]
                    self.assertEqual(self.progression.level(identifier), 10)
                    self.assertEqual(self.progression[identifier].xp_into_level, 25)
                    self.assertEqual(attributes.to_dict()['attributes'], character_stats(identifier, 10))
                    self.assertEqual((attributes.current_hp, attributes.current_mp), (17, 3))

    def test_growth_adds_to_preserved_legacy_baseline_and_keeps_modifier_owners(self):
        attributes = self.party.characters['mira']
        attributes.apply_growth({'hp': 31, 'str': 17})
        attributes.set_modifiers('engineered_armor', {'hp': 100, 'def': 7})
        attributes.set_current(hp=201, mp=4)
        before = attributes.to_dict()['attributes']
        modifiers = deepcopy(attributes._modifiers)
        identity = attributes
        plan = self.plan(active=('mira',))
        entry = plan['characters']['mira']
        self.assertTrue(self.progression.apply(plan))
        self.assertIs(self.party.characters['mira'], identity)
        self.assertEqual(attributes._modifiers, modifiers)
        self.assertEqual((attributes.current_hp, attributes.current_mp), (201, 4))
        self.assertEqual(entry['stats_before'], before)
        self.assertEqual(attributes.to_dict()['attributes'], entry['stats_after'])
        self.assertEqual(attributes.value('def'), entry['stats_after']['def']+7)

    def test_level_cap_reports_overflow_and_never_exceeds_attribute_caps(self):
        source = self.progression.to_dict()
        source['characters']['caelan']['total_xp'] = MAX_TOTAL_XP-5
        self.assertTrue(self.progression.restore(source))
        attributes = self.party.characters['caelan']
        attributes._attributes = dict(ATTRIBUTE_CAPS)
        attributes.set_current(hp=0, mp=0)
        plan = self.plan(999, ('caelan',))
        entry = plan['characters']['caelan']
        self.assertEqual((entry['accepted_xp'], entry['discarded_xp']), (5, 994))
        self.assertEqual((entry['old_level'], entry['new_level']), (99, 100))
        self.assertEqual(entry['stats_before'], entry['stats_after'])
        self.assertTrue(self.progression.apply(plan))
        self.assertEqual(self.progression['caelan'].total_xp, MAX_TOTAL_XP)
        self.assertEqual((attributes.current_hp, attributes.current_mp), (0, 0))
        capped = self.plan(999, ('caelan',))
        self.assertEqual(capped['characters']['caelan']['accepted_xp'], 0)
        self.assertTrue(self.progression.apply(capped))  # Safe no-op; receipt owns settlement.

    def test_growth_never_reduces_an_existing_oversized_in_memory_base(self):
        # Save validation remains capped. Defend against an external owner
        # supplying a larger in-memory base without silently reducing it.
        attributes = self.party.characters['caelan']
        attributes._attributes.update(str=1500, speed=300)
        attributes.set_current(hp=17, mp=3)
        plan = self.plan(active=('caelan',))
        self.assertTrue(CharacterProgression.valid_plan(plan))
        self.assertEqual(plan['characters']['caelan']['stats_before']['str'], 1500)
        self.assertEqual(plan['characters']['caelan']['stats_after']['str'], 1500)
        self.assertTrue(self.progression.apply(plan))
        self.assertEqual((attributes.base_value('str'), attributes.base_value('speed')), (1500, 300))
        self.assertEqual((attributes.value('str'), attributes.value('speed')), (999, 255))

    def test_plan_validation_rejects_forged_awards_and_stats_without_partial_application(self):
        original = self.plan()
        mutations = (
            lambda p:p.update(extra=True),
            lambda p:p.update(version=True),
            lambda p:p.update(amount=True),
            lambda p:p['active_ids'].append('caelan'),
            lambda p:p['end_hp'].update(rhea=1),
            lambda p:p['end_hp'].update(caelan=True),
            lambda p:p['characters'].pop('mira'),
            lambda p:p['characters']['mira'].update(character_id='rhea'),
            lambda p:p['characters']['mira'].update(requested_xp=1),
            lambda p:p['characters']['mira'].update(new_total_xp=999999),
            lambda p:p['characters']['mira'].update(old_level=True),
            lambda p:p['characters']['mira']['stat_gains'].update(str=999),
            lambda p:p['characters']['mira']['stat_gains'].update(hp=True),
            lambda p:p['characters']['mira']['stats_before'].update(str=-1),
            lambda p:p['characters']['mira']['stats_after'].update(hp=9999),
        )
        before = self.state()
        for mutate in mutations:
            candidate = deepcopy(original);mutate(candidate)
            with self.subTest(candidate=candidate):
                self.assertFalse(CharacterProgression.valid_plan(candidate))
                self.assertFalse(self.progression.apply(candidate))
                self.assertEqual(self.state(), before)

    def test_changed_before_xp_or_any_participating_stat_rejects_complete_award(self):
        plan = self.plan()
        self.progression.records['lucan'].award_xp(1)
        before = self.state()
        self.assertFalse(self.progression.apply(plan))
        self.assertEqual(self.state(), before)
        self.progression.records['lucan'] = CharacterLevel('lucan')
        self.party.characters['lucan'].apply_growth({'str': 1})
        before = self.state()
        self.assertFalse(self.progression.apply(plan))
        self.assertEqual(self.state(), before)

    def test_current_resource_changes_between_preview_and_award_do_not_change_growth(self):
        plan = self.plan(active=('caelan',))
        self.party.characters['caelan'].set_current(hp=0, mp=0)
        self.assertTrue(self.progression.apply(plan))
        self.assertEqual((self.party.characters['caelan'].current_hp,
                          self.party.characters['caelan'].current_mp), (0, 0))

    def test_save_roundtrip_is_strict_detached_and_does_not_mutate_attributes(self):
        self.assertTrue(self.progression.apply(self.plan()))
        snapshot = json.loads(json.dumps(self.progression.to_dict()))
        attributes = deepcopy(self.party.to_dict())
        copy = CharacterProgression(self.party)
        self.assertTrue(copy.restore(snapshot))
        self.assertEqual(copy.to_dict(), snapshot)
        self.assertEqual(self.party.to_dict(), attributes)
        snapshot['characters']['mira']['total_xp'] += 1
        self.assertNotEqual(copy.to_dict(), snapshot)
        self.assertTrue(CharacterProgression.valid_journey({'character_levels': copy.to_dict()}))
        self.assertFalse(CharacterProgression.valid_journey(None))

    def test_invalid_saved_records_leave_current_levels_and_party_intact(self):
        original = self.progression.to_dict()
        mutations = (
            lambda p:p.update(extra=True),
            lambda p:p.update(version=True),
            lambda p:p['characters'].pop('edran'),
            lambda p:p['characters'].update(bot=p['characters']['mira']),
            lambda p:p['characters']['mira'].update(character_id='rhea'),
            lambda p:p['characters']['mira'].update(total_xp=True),
            lambda p:p['characters']['mira'].update(total_xp=-1),
            lambda p:p['characters']['mira'].update(total_xp=MAX_TOTAL_XP+1),
        )
        before = self.state()
        for mutate in mutations:
            candidate = deepcopy(original);mutate(candidate)
            with self.subTest(record=candidate):
                self.assertFalse(CharacterProgression.valid_snapshot(candidate))
                self.assertFalse(self.progression.restore(candidate))
                self.assertEqual(self.state(), before)

    def test_invalid_preview_inputs_leave_levels_and_stats_intact(self):
        before = self.state()
        for amount, active, hp in ((True, ('caelan',), {'caelan': 1}),
                                   (-1, ('caelan',), {'caelan': 1}),
                                   (1, (), {}), (1, ('unknown_actor',), {'unknown_actor': 1}),
                                   (1, ('caelan',), {'caelan': True}),
                                   (1, ('caelan',), {'caelan': 10000})):
            with self.subTest(amount=amount, active=active, hp=hp):
                with self.assertRaises((ValueError, TypeError)):
                    self.progression.preview(amount, active, hp)
                self.assertEqual(self.state(), before)


if __name__ == '__main__':
    unittest.main()
