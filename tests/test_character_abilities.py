"""Character skill registrations, permanent unlocks, and owned weapon state."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from aether_lattice import AetherLattice, LatticeBoard
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
        self.lattice = AetherLattice()
        self.abilities = CharacterAbilities(self.inventory, self.lattice)

    def snapshot(self):
        return (self.inventory.to_dict(), self.abilities.to_dict(), self.lattice.to_dict())

    def test_lattice_builder_preserves_weapon_and_future_character_definitions(self):
        from tools import build_caelan_lattice
        catalog = deepcopy(self.abilities.catalog)
        catalog['abilities']['fixture_future_spell'] = {
            'name': 'Future Spell Fixture', 'description': 'A catalog extension fixture.',
            'kind': 'spell'}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'catalog.json'
            path.write_text(json.dumps(catalog))
            with patch.object(build_caelan_lattice, 'ABILITIES', path):
                board, rebuilt = build_caelan_lattice.build()
        for identifier in ('aether_edge', 'fixture_future_spell'):
            self.assertEqual(rebuilt['abilities'][identifier], catalog['abilities'][identifier])
        self.assertEqual(json.loads(json.dumps(board)), self.lattice.board.data)
        self.assertNotIn('aether_edge', {node.get('ability_id') for node in board['nodes'].values()})

    def test_new_journey_is_unarmed_and_has_only_basic_magicks(self):
        self.assertEqual(self.abilities.known_abilities(), frozenset({'basic_magicks'}))
        self.assertEqual(self.abilities.skill_ids(), ())
        self.assertFalse(self.abilities.has_weapon())
        self.assertEqual(self.inventory.entries(), [])
        self.assertNotIn('aether_edge', self.abilities.known_abilities())
        self.assertNotIn('focused_strike', self.abilities.known_abilities())
        self.assertEqual(Inventory().entries('weapons'), [])
        self.assertFalse(any(record['category'] == 'weapons'
                             for record in Inventory().definitions.values()))

    def test_future_character_profiles_are_registered_without_free_skills(self):
        expected = {'caelan': ('Caelan', 'Spellblade'), 'mira': ('Mira', 'Machinist'),
                    'lucan': ('Lucan', 'Knight'), 'rhea': ('Rhea', 'Aethermage'),
                    'edran': ('Edran', 'Sage')}
        self.assertEqual(set(self.abilities.characters), set(expected))
        for identifier, (name, job) in expected.items():
            with self.subTest(character=identifier):
                profile = self.abilities.characters[identifier]
                self.assertEqual((profile['name'], profile['job']), (name, job))
                self.assertTrue(all(isinstance(profile[key], dict)
                                    for key in ('skills', 'spells', 'abilities')))
                if identifier != 'caelan':
                    self.assertEqual(self.abilities.known_abilities(identifier), frozenset())
                    self.assertEqual(self.abilities.skill_ids(identifier), ())
                    self.assertFalse(self.abilities.has_weapon(identifier))
                    self.assertFalse(any(profile[key] for key in ('skills', 'spells', 'abilities')))

    def test_only_aether_edge_uses_first_weapon_and_lattice_rewards_keep_their_ids(self):
        profile = self.abilities.characters['caelan']
        registrations = {key: value for category in ('skills', 'spells', 'abilities')
                         for key, value in profile[category].items()}
        first_weapon = {key for key, value in registrations.items()
                        if value['unlock'] == 'first_weapon'}
        self.assertEqual(first_weapon, {'aether_edge'})
        self.assertEqual(registrations['basic_magicks'], {'unlock': 'starting'})
        rewards = {node['ability_id'] for node in self.lattice.board.nodes.values()
                   if node['kind'] == 'ability'}
        self.assertEqual({key for key, value in registrations.items()
                          if value['unlock'] == 'lattice'}, rewards)
        definition = self.abilities.definitions['aether_edge']
        self.assertEqual(set(definition), {'name', 'description', 'kind'})
        self.assertEqual((definition['name'], definition['kind']), ('Aether Edge', 'technique'))
        self.assertIn('non-elemental', definition['description'].lower())
        self.assertIn('weapon', definition['description'].lower())

    def test_acquisition_adds_and_equips_a_real_catalog_weapon_and_grants_only_edge(self):
        before_lattice = self.lattice.to_dict()
        self.assertTrue(self.abilities.acquire_weapon('caelan', 'fixture_blade'))
        self.assertEqual(self.inventory.quantity('fixture_blade'), 1)
        self.assertTrue(self.abilities.has_weapon())
        self.assertEqual(self.abilities.to_dict()['characters']['caelan'],
                         {'equipped_weapon': 'fixture_blade', 'first_weapon_acquired': True})
        self.assertEqual(self.abilities.known_abilities(), frozenset({'basic_magicks', 'aether_edge'}))
        self.assertEqual(self.abilities.skill_ids(), ('aether_edge',))
        self.assertEqual(self.lattice.to_dict(), before_lattice)
        for identifier in ('mira', 'lucan', 'rhea', 'edran'):
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
        self.assertEqual(self.abilities.known_abilities('mira'), frozenset())
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
        other = CharacterAbilities(self.inventory, self.lattice)
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

    def test_lattice_unlocks_are_derived_live_and_skill_order_matches_catalog(self):
        self.assertTrue(self.abilities.acquire_weapon('caelan', 'fixture_blade'))
        self.assertTrue(self.lattice.award_rewards('ability:training', {'caelan': 100000}))
        for node in ('mend_01', 'brace_01', 'focused_strike_01'):
            self.assertTrue(self.lattice.move(node))
            self.assertTrue(self.lattice.activate(node))
        expected = frozenset({'basic_magicks', 'aether_edge', 'mend', 'brace', 'focused_strike'})
        self.assertEqual(self.abilities.known_abilities(), expected)
        self.assertEqual(self.abilities.skill_ids(), tuple(
            key for key, definition in self.abilities.definitions.items()
            if definition['kind'] == 'technique' and key in expected))
        self.assertNotIn('mend', self.abilities.skill_ids())
        self.lattice.reset()
        self.assertEqual(self.abilities.known_abilities(), frozenset({'basic_magicks', 'aether_edge'}))

    def test_catalog_addition_is_compatible_with_current_and_archived_lattice_boards(self):
        board = self.lattice.board
        self.assertIn('aether_edge', board.abilities)
        self.assertNotIn('aether_edge', {node.get('ability_id') for node in board.nodes.values()})
        for filename in ('aether_lattice_v1.json', 'aether_lattice_v2.json'):
            data = json.loads((ROOT/'assets/progression'/filename).read_text(encoding='utf-8'))
            archive = LatticeBoard(data, self.abilities.catalog)
            self.assertIn('aether_edge', archive.abilities)
            self.assertEqual(archive.starting_abilities['caelan'], ['basic_magicks'])

    def test_round_trip_restores_equipment_and_permanent_unequipped_unlock_without_grants(self):
        self.assertTrue(self.abilities.acquire_weapon('caelan', 'fixture_blade'))
        self.assertTrue(self.abilities.equip_weapon('caelan', None))
        self.assertTrue(self.abilities.acquire_weapon('mira', 'fixture_spear'))
        saved = self.abilities.to_dict()
        inventory_before = self.inventory.to_dict()
        other = CharacterAbilities(self.inventory, self.lattice)
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
                    CharacterAbilities(self.inventory, self.lattice, catalog=catalog, characters=characters)
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
                    CharacterAbilities(self.inventory, self.lattice, catalog=base_catalog, characters=profiles)
                self.assertEqual(profiles, original)

    def test_journey_validation_handles_legacy_and_rejects_explicit_invalid_blocks(self):
        canonical_inventory = Inventory()
        canonical_lattice = AetherLattice()
        canonical = CharacterAbilities(canonical_inventory, canonical_lattice)
        journey = {'inventory': canonical_inventory.to_dict(),
                   'aether_lattice': canonical_lattice.to_dict(),
                   'character_abilities': canonical.to_dict()}
        self.assertTrue(CharacterAbilities.valid_journey(journey))
        self.assertTrue(CharacterAbilities.valid_journey({}))
        self.assertTrue(CharacterAbilities.valid_journey({
            'inventory': canonical_inventory.to_dict(),
            'aether_lattice': canonical_lattice.to_dict()}))
        for block in ('inventory', 'aether_lattice', 'character_abilities'):
            for invalid in (None, True, [], {}):
                with self.subTest(block=block, invalid=invalid):
                    bad = deepcopy(journey);bad[block] = invalid
                    self.assertFalse(CharacterAbilities.valid_journey(bad))
        for invalid in (None, True, []):
            self.assertFalse(CharacterAbilities.valid_journey(invalid))


if __name__ == '__main__':unittest.main()
