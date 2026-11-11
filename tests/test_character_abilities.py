"""Character skill registrations, permanent unlocks, and owned weapon state."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from character_abilities import CharacterAbilities
from inventory import Inventory, MAX_QUANTITY


ROOT = Path(__file__).resolve().parents[1]


def weapon_inventory():
    """Use test weapons without adding equipment to the live item catalog."""
    catalog = Inventory().catalog
    for identifier, category in (('fixture_blade', 'weapons'),
                                 ('fixture_spear', 'weapons'),
                                 ('fixture_coat', 'armor')):
        catalog['items'][identifier] = {
            'name': identifier.replace('_', ' ').title(),
            'description': 'Equipment used only by the character skill tests.',
            'category': category,
        }
    return Inventory(catalog)


class CharacterAbilitiesTests(unittest.TestCase):
    def setUp(self):
        self.inventory = weapon_inventory()
        self.abilities = CharacterAbilities(self.inventory)

    def snapshot(self):
        return (self.inventory.to_dict(), self.abilities.to_dict())

    def test_new_journey_is_unarmed_and_has_only_basic_magicks(self):
        self.assertEqual(self.abilities.known_abilities(), frozenset({'basic_magicks'}))
        self.assertEqual(self.abilities.skill_ids(), ())
        self.assertFalse(self.abilities.has_weapon())
        self.assertEqual(self.inventory.entries(), [])
        self.assertNotIn('aether_edge', self.abilities.known_abilities())
        self.assertNotIn('focused_strike', self.abilities.known_abilities())
        self.assertEqual(Inventory().entries('weapons'), [])
        self.assertEqual(Inventory().definitions['caelan_gearblade']['category'], 'weapons')
        self.assertEqual(Inventory().quantity('caelan_gearblade'), 0)

    def test_character_profiles_register_miras_starters_without_granting_other_guests_skills(self):
        expected = {'caelan': ('Caelan', 'Spellblade'), 'mira': ('Mira', 'Engineer'),
                    'lucan': ('Lucan', 'Knight'), 'rhea': ('Rhea', 'Aethermage'),
                    'edran': ('Edran', 'Sage')}
        self.assertEqual(set(self.abilities.characters), set(expected))
        for identifier, (name, job) in expected.items():
            with self.subTest(character=identifier):
                profile = self.abilities.characters[identifier]
                self.assertEqual((profile['name'], profile['job']), (name, job))
                self.assertTrue(all(isinstance(profile[key], dict)
                                    for key in ('skills', 'spells', 'abilities')))
                if identifier == 'mira':
                    self.assertEqual(self.abilities.known_abilities(identifier),
                                     frozenset({'arm_rig', 'charged_bolt', 'bulwark', 'repair_pulse', 'impact_bolt', 'arc_discharge'}))
                    self.assertEqual(self.abilities.skill_ids(identifier), ('charged_bolt', 'bulwark', 'repair_pulse', 'impact_bolt', 'arc_discharge'))
                    self.assertFalse(self.abilities.has_weapon(identifier))
                    self.assertEqual(profile['skills'], {key: {'unlock': 'starting'} for key in ('charged_bolt', 'bulwark', 'repair_pulse', 'impact_bolt', 'arc_discharge')})
                    self.assertEqual(profile['abilities'], {'arm_rig': {'unlock': 'starting'}})
                    self.assertEqual(profile['spells'], {})
                elif identifier != 'caelan':
                    self.assertEqual(self.abilities.known_abilities(identifier), frozenset())
                    self.assertEqual(self.abilities.skill_ids(identifier), ())
                    self.assertFalse(self.abilities.has_weapon(identifier))
                    self.assertFalse(any(profile[key] for key in ('skills', 'spells', 'abilities')))

    def test_only_aether_edge_uses_first_weapon_and_other_unlocks_require_learning(self):
        profile = self.abilities.characters['caelan']
        registrations = {key: value for category in ('skills', 'spells', 'abilities')
                         for key, value in profile[category].items()}
        first_weapon = {key for key, value in registrations.items()
                        if value['unlock'] == 'first_weapon'}
        self.assertEqual(first_weapon, {'aether_edge'})
        self.assertEqual(registrations['basic_magicks'], {'unlock': 'starting'})
        learned = {key for key, value in registrations.items() if value['unlock'] == 'learned'}
        self.assertEqual(len(learned), 23)
        self.assertTrue({'brace', 'mend', 'aether_dart', 'flame_edge', 'ice_edge'}.issubset(learned))
        self.assertTrue(learned.isdisjoint(self.abilities.known_abilities()))
        definition = self.abilities.definitions['aether_edge']
        self.assertEqual(set(definition), {'name', 'description', 'kind'})
        self.assertEqual((definition['name'], definition['kind']), ('Aether Edge', 'technique'))
        self.assertIn('non-elemental', definition['description'].lower())
        self.assertIn('weapon', definition['description'].lower())

    def test_acquisition_adds_and_equips_a_real_catalog_weapon_and_grants_only_edge(self):
        self.assertTrue(self.abilities.acquire_weapon('caelan', 'fixture_blade'))
        self.assertEqual(self.inventory.quantity('fixture_blade'), 1)
        self.assertTrue(self.abilities.has_weapon())
        self.assertEqual(self.abilities.to_dict()['characters']['caelan'],
                         {'equipped_weapon': 'fixture_blade', 'first_weapon_acquired': True})
        self.assertEqual(self.abilities.known_abilities(), frozenset({'basic_magicks', 'aether_edge'}))
        self.assertEqual(self.abilities.skill_ids(), ('aether_edge',))
        self.assertEqual(self.abilities.known_abilities('mira'), frozenset({'arm_rig', 'charged_bolt', 'bulwark', 'repair_pulse', 'impact_bolt', 'arc_discharge'}))
        self.assertEqual(self.abilities.skill_ids('mira'), ('charged_bolt', 'bulwark', 'repair_pulse', 'impact_bolt', 'arc_discharge'))
        for identifier in ('lucan', 'rhea', 'edran'):
            self.assertEqual(self.abilities.known_abilities(identifier), frozenset())

    def test_equip_requires_owned_weapon_and_first_weapon_history_survives_unequip(self):
        self.assertFalse(self.abilities.equip_weapon('caelan', 'fixture_blade'))
        self.assertTrue(self.inventory.add('fixture_blade'))
        self.assertTrue(self.abilities.equip_weapon('caelan', 'fixture_blade'))
        self.assertTrue(self.abilities.has_weapon())
        self.assertTrue(self.abilities.equip_weapon('caelan', None))
        self.assertFalse(self.abilities.has_weapon())
        self.assertEqual(self.inventory.quantity('fixture_blade'), 1)
        self.assertIn('aether_edge', self.abilities.known_abilities())
        self.assertEqual(self.abilities.skill_ids(), ('aether_edge',))
        self.assertTrue(self.abilities.to_dict()['characters']['caelan']['first_weapon_acquired'])

    def test_story_gift_equips_blade_but_defers_skill_until_successful_lesson(self):
        self.assertTrue(self.abilities.acquire_weapon('caelan', 'caelan_gearblade', learn_starter=False))
        self.assertTrue(self.abilities.has_weapon())
        self.assertTrue(self.abilities.starter_skills_pending())
        self.assertEqual(self.abilities.known_abilities(), frozenset({'basic_magicks'}))
        self.assertEqual(self.abilities.skill_ids(), ())
        self.assertEqual(self.abilities.to_dict()['deferred_weapon_training'], ['caelan'])
        self.assertEqual(self.abilities.to_dict()['characters']['caelan'],
                         {'equipped_weapon': 'caelan_gearblade', 'first_weapon_acquired': True})
        before = self.inventory.to_dict()
        self.assertTrue(self.abilities.learn_first_weapon_skills())
        self.assertTrue(self.abilities.learn_first_weapon_skills())
        self.assertEqual(self.inventory.to_dict(), before)
        self.assertFalse(self.abilities.starter_skills_pending())
        self.assertEqual(self.abilities.skill_ids(), ('aether_edge',))
        self.assertNotIn('deferred_weapon_training', self.abilities.to_dict())
        self.assertTrue({'nature_edge','aqua_edge','flame_edge'}.isdisjoint(self.abilities.known_abilities()))

    def test_pending_lesson_round_trip_re_equipping_and_reset_do_not_grant_knowledge(self):
        self.assertTrue(self.abilities.acquire_weapon('caelan', 'caelan_gearblade', learn_starter=False))
        self.assertTrue(self.abilities.equip_weapon('caelan', None))
        self.assertFalse(self.abilities.learn_first_weapon_skills())
        saved = self.abilities.to_dict()
        other = CharacterAbilities(self.inventory)
        self.assertTrue(other.restore(saved))
        self.assertEqual(other.to_dict(), saved)
        self.assertTrue(other.starter_skills_pending())
        self.assertNotIn('aether_edge', other.known_abilities())
        self.assertTrue(other.equip_weapon('caelan', 'caelan_gearblade'))
        self.assertNotIn('aether_edge', other.known_abilities())
        self.assertTrue(other.learn_first_weapon_skills())
        self.assertTrue(other.equip_weapon('caelan', None))
        self.assertIn('aether_edge', other.known_abilities())
        other.reset()
        self.assertFalse(other.starter_skills_pending())
        self.assertNotIn('aether_edge', other.known_abilities())
        self.assertNotIn('deferred_weapon_training', other.to_dict())

    def test_version_one_history_without_pending_extension_keeps_earned_skills(self):
        self.assertTrue(self.abilities.acquire_weapon('caelan', 'caelan_gearblade', learn_starter=False))
        saved = self.abilities.to_dict()
        saved.pop('deferred_weapon_training')
        self.assertTrue(self.abilities.restore(saved))
        self.assertFalse(self.abilities.starter_skills_pending())
        self.assertIn('aether_edge', self.abilities.known_abilities())

    def test_invalid_pending_lesson_snapshots_reject_atomically(self):
        self.assertTrue(self.abilities.acquire_weapon('caelan', 'caelan_gearblade', learn_starter=False))
        saved = self.abilities.to_dict()
        before = self.snapshot()
        for value in (None, True, {}, 'caelan', [True], [[]], ['missing'], ['caelan','caelan']):
            with self.subTest(value=value):
                bad = deepcopy(saved);bad['deferred_weapon_training'] = value
                self.assertFalse(self.abilities.restore(bad))
                self.assertEqual(self.snapshot(), before)
        bad = deepcopy(saved)
        bad['deferred_weapon_training'] = ['mira']
        self.assertFalse(self.abilities.restore(bad))
        self.assertEqual(self.snapshot(), before)
        for value in (None, 1, 'yes'):
            self.assertFalse(self.abilities.acquire_weapon('caelan','caelan_gearblade',learn_starter=value))
            self.assertEqual(self.snapshot(), before)

    def test_another_deferred_gift_cannot_remove_an_already_earned_skill(self):
        self.assertTrue(self.abilities.acquire_weapon('caelan', 'fixture_blade'))
        self.assertTrue(self.abilities.acquire_weapon('caelan', 'caelan_gearblade', learn_starter=False))
        self.assertIn('aether_edge', self.abilities.known_abilities())
        self.assertFalse(self.abilities.starter_skills_pending())

    def test_journey_validator_checks_pending_training_against_saved_ownership(self):
        inventory = Inventory()
        abilities = CharacterAbilities(inventory)
        self.assertTrue(abilities.acquire_weapon('caelan','caelan_gearblade',learn_starter=False))
        journey = dict(inventory=inventory.to_dict(),
                       character_abilities=abilities.to_dict())
        self.assertTrue(CharacterAbilities.valid_journey(journey))
        journey['inventory']['items'].clear()
        self.assertFalse(CharacterAbilities.valid_journey(journey))

    def test_invalid_acquisition_and_equipment_leave_inventory_and_unlocks_unchanged(self):
        self.assertTrue(self.inventory.add('fixture_coat'))
        self.assertTrue(self.inventory.add('aether_diamond'))
        before = self.snapshot()
        for character, item in (('missing', 'fixture_blade'), ([], 'fixture_blade'),
                                ('caelan', 'missing'), ('caelan', 'fixture_coat'),
                                ('caelan', 'aether_diamond'), ('caelan', []),
                                ('caelan', True)):
            with self.subTest(character=character, item=item):
                self.assertFalse(self.abilities.acquire_weapon(character, item))
                self.assertFalse(self.abilities.equip_weapon(character, item))
                self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.abilities.acquire_weapon('caelan', None))
        self.assertEqual(self.snapshot(), before)

    def test_inventory_refusal_does_not_equip_or_unlock(self):
        self.assertTrue(self.inventory.add('fixture_blade', MAX_QUANTITY))
        before = self.snapshot()
        self.assertFalse(self.abilities.acquire_weapon('caelan', 'fixture_blade'))
        self.assertEqual(self.snapshot(), before)
        with patch.object(self.inventory, 'add', return_value=False):
            self.assertFalse(self.abilities.acquire_weapon('caelan', 'fixture_spear'))
        self.assertEqual(self.snapshot(), before)

    def test_equipment_uses_owned_copies_and_acquisition_adds_a_new_copy(self):
        self.assertTrue(self.inventory.add('fixture_blade'))
        self.assertTrue(self.abilities.equip_weapon('caelan', 'fixture_blade'))
        before = self.snapshot()
        self.assertFalse(self.abilities.equip_weapon('mira', 'fixture_blade'))
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(self.inventory.add('fixture_blade'))
        self.assertTrue(self.abilities.equip_weapon('mira', 'fixture_blade'))
        self.assertTrue(self.abilities.equip_weapon('caelan', 'fixture_blade'))
        self.assertEqual(self.inventory.quantity('fixture_blade'), 2)
        self.assertTrue(self.abilities.has_weapon())
        self.assertTrue(self.abilities.has_weapon('mira'))
        self.assertEqual(self.abilities.known_abilities('mira'), frozenset({'arm_rig', 'charged_bolt', 'bulwark', 'repair_pulse', 'impact_bolt', 'arc_discharge'}))
        self.assertEqual(self.abilities.skill_ids('mira'), ('charged_bolt', 'bulwark', 'repair_pulse', 'impact_bolt', 'arc_discharge'))
        self.assertTrue(self.abilities.acquire_weapon('lucan', 'fixture_blade'))
        self.assertEqual(self.inventory.quantity('fixture_blade'), 3)
        self.assertTrue(self.abilities.has_weapon('lucan'))

    def test_quantity_shrink_keeps_earlier_profile_owner_and_does_not_reequip_others(self):
        for character in ('edran', 'mira', 'caelan'):
            self.assertTrue(self.abilities.acquire_weapon(character, 'fixture_blade'))
        self.assertTrue(self.inventory.remove('fixture_blade', 2))
        self.abilities.reconcile_equipment()
        self.assertTrue(self.abilities.has_weapon('caelan'))
        for character in ('mira', 'edran'):
            self.assertFalse(self.abilities.has_weapon(character))
            self.assertEqual(self.abilities.to_dict()['characters'][character],
                             {'equipped_weapon': None, 'first_weapon_acquired': True})
        self.assertTrue(self.inventory.add('fixture_blade', 2))
        self.assertFalse(self.abilities.has_weapon('mira'))
        self.assertFalse(self.abilities.has_weapon('edran'))

    def test_restore_allows_distinct_owned_copies_and_rejects_overcommitted_counts(self):
        self.assertTrue(self.abilities.acquire_weapon('caelan', 'fixture_blade'))
        self.assertTrue(self.abilities.acquire_weapon('mira', 'fixture_blade'))
        saved = self.abilities.to_dict()
        other = CharacterAbilities(self.inventory)
        self.assertTrue(other.restore(saved))
        self.assertTrue(other.has_weapon('caelan'))
        self.assertTrue(other.has_weapon('mira'))
        before = self.snapshot()
        bad = deepcopy(saved)
        bad['characters']['edran'] = deepcopy(bad['characters']['caelan'])
        self.assertFalse(self.abilities.restore(bad))
        self.assertEqual(self.snapshot(), before)

    def test_missing_owned_weapon_is_unusable_but_earned_skill_remains_known(self):
        self.assertTrue(self.abilities.acquire_weapon('caelan', 'fixture_blade'))
        self.assertTrue(self.inventory.remove('fixture_blade'))
        self.assertFalse(self.abilities.has_weapon())
        self.assertIn('aether_edge', self.abilities.known_abilities())
        self.assertTrue(self.inventory.add('fixture_blade'))
        self.assertFalse(self.abilities.has_weapon())
        saved = self.abilities.to_dict()
        self.assertEqual(saved['characters']['caelan'],
                         {'equipped_weapon': None, 'first_weapon_acquired': True})
        self.assertTrue(self.abilities.restore(saved))
        self.assertTrue(self.abilities.equip_weapon('caelan', 'fixture_blade'))
        self.assertTrue(self.abilities.has_weapon())

    def test_explicit_learned_unlocks_round_trip_and_skill_order_matches_catalog(self):
        self.assertTrue(self.abilities.acquire_weapon('caelan', 'fixture_blade'))
        for ability in ('mend', 'brace', 'focused_strike'):
            self.assertTrue(self.abilities.learn_ability('caelan', ability))
        expected = frozenset({'basic_magicks', 'aether_edge', 'mend', 'brace', 'focused_strike'})
        self.assertEqual(self.abilities.known_abilities(), expected)
        self.assertEqual(self.abilities.skill_ids(), tuple(
            key for key, definition in self.abilities.definitions.items()
            if definition['kind'] == 'technique' and key in expected))
        self.assertNotIn('mend', self.abilities.skill_ids())
        saved = self.abilities.to_dict()
        other = CharacterAbilities(self.inventory)
        self.assertTrue(other.restore(saved))
        self.assertEqual(other.known_abilities(), expected)
        self.assertEqual(other.to_dict(), saved)
        self.abilities.reset()
        self.assertEqual(self.abilities.known_abilities(), frozenset({'basic_magicks'}))

    def test_learning_requires_registered_explicit_unlock_and_never_grants_equipment(self):
        before = self.snapshot()
        for character, ability in (
                ('missing', 'mend'), ([], 'mend'), (None, 'mend'),
                ('mira', 'mend'), ('caelan', 'charged_bolt'), ('caelan', 'missing'),
                ('caelan', 'basic_magicks'), ('caelan', 'aether_edge'),
                ('caelan', None), ('caelan', True), ('caelan', [])):
            with self.subTest(character=character, ability=ability):
                self.assertFalse(self.abilities.learn_ability(character, ability))
                self.assertEqual(self.snapshot(), before)
        self.assertTrue(self.abilities.learn_ability('caelan', 'aether_dart'))
        learned = self.snapshot()
        self.assertFalse(self.abilities.learn_ability('caelan', 'aether_dart'))
        self.assertEqual(self.snapshot(), learned)
        self.assertEqual(self.inventory.to_dict(), before[0])
        self.assertFalse(self.abilities.has_weapon())
        self.assertEqual(self.abilities.known_abilities(),
                         frozenset({'basic_magicks', 'aether_dart'}))

    def test_learned_snapshot_validation_is_strict_and_preserves_all_state_on_failure(self):
        self.assertTrue(self.abilities.acquire_weapon('caelan', 'caelan_gearblade',
                                                     learn_starter=False))
        self.assertTrue(self.abilities.grant_gem('ice'))
        self.assertTrue(self.abilities.set_active_gem('ice'))
        self.assertTrue(self.abilities.learn_ability('caelan', 'mend'))
        saved, before = self.abilities.to_dict(), self.snapshot()
        invalid = (None, True, [], 'mend', {'missing': ['mend']},
                   {'mira': ['mend']}, {'caelan': []}, {'caelan': 'mend'},
                   {'caelan': [None]}, {'caelan': [[]]}, {'caelan': [True]},
                   {'caelan': ['missing']}, {'caelan': ['basic_magicks']},
                   {'caelan': ['aether_edge']}, {'caelan': ['mend', 'mend']})
        for learned in invalid:
            with self.subTest(learned=learned):
                bad = deepcopy(saved);bad['learned_abilities'] = learned
                self.assertFalse(self.abilities.restore(bad))
                self.assertEqual(self.snapshot(), before)
        clone = CharacterAbilities(self.inventory)
        self.assertTrue(clone.restore(saved))
        self.assertTrue(clone.starter_skills_pending())
        self.assertEqual(clone.active_gem(), 'ice')
        self.assertEqual(clone.known_abilities(), frozenset({'basic_magicks', 'mend'}))
        saved['learned_abilities']['caelan'].append('aether_dart')
        self.assertNotIn('aether_dart', clone.known_abilities())
        exported = clone.to_dict()
        exported['learned_abilities']['caelan'].clear()
        self.assertIn('mend', clone.known_abilities())

    def test_round_trip_restores_equipment_and_permanent_unequipped_unlock_without_grants(self):
        self.assertTrue(self.abilities.acquire_weapon('caelan', 'fixture_blade'))
        self.assertTrue(self.abilities.equip_weapon('caelan', None))
        self.assertTrue(self.abilities.acquire_weapon('mira', 'fixture_spear'))
        saved = self.abilities.to_dict()
        inventory_before = self.inventory.to_dict()
        other = CharacterAbilities(self.inventory)
        for _ in range(2):
            self.assertTrue(other.restore(saved))
            self.assertEqual(other.to_dict(), saved)
            self.assertFalse(other.has_weapon())
            self.assertTrue(other.has_weapon('mira'))
            self.assertIn('aether_edge', other.known_abilities())
            self.assertEqual(self.inventory.to_dict(), inventory_before)
        saved['characters']['caelan']['first_weapon_acquired'] = False
        self.assertIn('aether_edge', other.known_abilities())

    def test_missing_legacy_state_resets_to_unarmed_without_inventing_history(self):
        self.assertTrue(self.abilities.acquire_weapon('caelan', 'fixture_blade'))
        inventory_before = self.inventory.to_dict()
        self.assertTrue(self.abilities.restore(None))
        self.assertFalse(self.abilities.has_weapon())
        self.assertEqual(self.abilities.known_abilities(), frozenset({'basic_magicks'}))
        self.assertEqual(self.inventory.to_dict(), inventory_before)
        self.assertTrue(self.abilities.equip_weapon('caelan', 'fixture_blade'))
        self.abilities.reset()
        self.assertFalse(self.abilities.has_weapon())
        self.assertEqual(self.abilities.known_abilities(), frozenset({'basic_magicks'}))
        self.assertEqual(self.inventory.to_dict(), inventory_before)

    def test_malformed_saves_fail_atomically_including_ownership_and_overcommitted_equipment(self):
        self.assertTrue(self.abilities.acquire_weapon('caelan', 'fixture_blade'))
        self.assertTrue(self.inventory.add('fixture_coat'))
        before = self.snapshot()
        state = self.abilities.to_dict()
        records = [True, [], {}, {'version': 1, 'characters': {}}]
        for field, value in (('version', True), ('version', 2), ('characters', [])):
            bad = deepcopy(state);bad[field] = value;records.append(bad)
        bad = deepcopy(state);bad['unexpected'] = True;records.append(bad)
        bad = deepcopy(state);bad['characters']['unknown'] = bad['characters'].pop('edran');records.append(bad)
        bad = deepcopy(state);bad['characters'].pop('mira');records.append(bad)
        for field, value in (('equipped_weapon', []), ('equipped_weapon', True),
                             ('equipped_weapon', 'missing'), ('equipped_weapon', 'fixture_spear'),
                             ('equipped_weapon', 'fixture_coat'),
                             ('first_weapon_acquired', 1), ('first_weapon_acquired', False)):
            bad = deepcopy(state);bad['characters']['caelan'][field] = value;records.append(bad)
        bad = deepcopy(state);bad['characters']['caelan']['unknown'] = True;records.append(bad)
        bad = deepcopy(state);bad['characters']['mira'] = deepcopy(bad['characters']['caelan']);records.append(bad)
        for record in records:
            with self.subTest(record=record):
                self.assertFalse(self.abilities.restore(record))
                self.assertEqual(self.snapshot(), before)

    def test_invalid_catalogs_fail_before_mutating_inputs(self):
        base_catalog = self.abilities.catalog
        characters = json.loads((ROOT/'assets/abilities/characters.json').read_text(encoding='utf-8'))
        bad_catalogs = []
        for field, value in (('version', True), ('version', 2), ('abilities', [])):
            bad = deepcopy(base_catalog);bad[field] = value;bad_catalogs.append(bad)
        for field, value in (('name', ''), ('description', ' '), ('kind', 'element')):
            bad = deepcopy(base_catalog);bad['abilities']['aether_edge'][field] = value;bad_catalogs.append(bad)
        bad = deepcopy(base_catalog);bad['abilities']['aether_edge']['mp_cost'] = 4;bad_catalogs.append(bad)
        for catalog in bad_catalogs:
            with self.subTest(catalog=catalog):
                original = deepcopy(catalog)
                with self.assertRaises(ValueError):
                    CharacterAbilities(self.inventory, catalog=catalog, characters=characters)
                self.assertEqual(catalog, original)
        bad_characters = []
        for field, value in (('version', True), ('characters', [])):
            bad = deepcopy(characters);bad[field] = value;bad_characters.append(bad)
        for field, value in (('name', ''), ('job', ' '), ('skills', [])):
            bad = deepcopy(characters);bad['characters']['caelan'][field] = value;bad_characters.append(bad)
        for record in ({'unlock': 'quest'}, {'unlock': True}, {'unlock': 'first_weapon', 'extra': 1}):
            bad = deepcopy(characters);bad['characters']['caelan']['skills']['aether_edge'] = record;bad_characters.append(bad)
        bad = deepcopy(characters);bad['characters']['caelan']['skills']['missing'] = {'unlock': 'starting'};bad_characters.append(bad)
        bad = deepcopy(characters);bad['characters']['caelan']['spells']['aether_edge'] = {'unlock': 'starting'};bad_characters.append(bad)
        for profiles in bad_characters:
            with self.subTest(characters=profiles):
                original = deepcopy(profiles)
                with self.assertRaises(ValueError):
                    CharacterAbilities(self.inventory, catalog=base_catalog, characters=profiles)
                self.assertEqual(profiles, original)

    def test_journey_validation_handles_legacy_and_rejects_explicit_invalid_blocks(self):
        canonical_inventory = Inventory()
        canonical = CharacterAbilities(canonical_inventory)
        journey = {'inventory': canonical_inventory.to_dict(),
                   'character_abilities': canonical.to_dict()}
        self.assertTrue(CharacterAbilities.valid_journey(journey))
        self.assertTrue(CharacterAbilities.valid_journey({}))
        self.assertTrue(CharacterAbilities.valid_journey({
            'inventory': canonical_inventory.to_dict()}))
        for block in ('inventory', 'character_abilities'):
            for invalid in (None, True, [], {}):
                with self.subTest(block=block, invalid=invalid):
                    bad = deepcopy(journey);bad[block] = invalid
                    self.assertFalse(CharacterAbilities.valid_journey(bad))
        for invalid in (None, True, []):
            self.assertFalse(CharacterAbilities.valid_journey(invalid))


if __name__ == '__main__':unittest.main()
