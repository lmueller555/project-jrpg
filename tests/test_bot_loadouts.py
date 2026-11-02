"""Starting bot ownership and strict, independent persistent loadouts."""
from copy import deepcopy
import json
import unittest

from aether_lattice import AetherLattice
from bot_loadouts import (BotLoadouts, CATALOG_PATH, load_bot_definitions,
                          starting_battle_loadouts)
from character_abilities import CharacterAbilities, starting_abilities
from inventory import Inventory


class BotLoadoutsTests(unittest.TestCase):
    def setUp(self):
        self.loadouts = BotLoadouts()

    def test_mira_starts_with_one_owned_bot_and_one_autonomous_ability(self):
        expected = {'mira': {'bot_id': 'rivet', 'ability_id': 'piston_jab'}}
        self.assertEqual(self.loadouts.battle_loadouts(), expected)
        self.assertEqual(starting_battle_loadouts(), expected)
        self.assertEqual(self.loadouts.owned_bots('mira'), frozenset({'rivet'}))
        for owner in ('caelan', 'lucan', 'rhea', 'edran', 'missing', [], None):
            self.assertEqual(self.loadouts.owned_bots(owner), frozenset())
        self.assertEqual(starting_abilities('mira'), frozenset({'rivet', 'overclock'}))
        self.assertEqual(starting_abilities('caelan'), frozenset({'basic_magicks'}))
        self.assertEqual(starting_abilities('missing'), frozenset())

    def test_bot_is_a_capability_and_its_strike_is_absent_from_miras_skills(self):
        abilities = CharacterAbilities(Inventory(), AetherLattice())
        self.assertEqual(abilities.known_abilities('mira'), frozenset({'overclock', 'rivet'}))
        self.assertEqual(abilities.skill_ids('mira'), ('overclock',))
        self.assertEqual(abilities.definitions['rivet']['kind'], 'capability')
        self.assertEqual(abilities.definitions['piston_jab']['kind'], 'technique')
        for identifier in ('deploy', 'deploy_rivet', 'repair', 'repair_rivet'):
            self.assertNotIn(identifier, abilities.definitions)
            self.assertNotIn(identifier, abilities.known_abilities('mira'))

    def test_ownership_does_not_create_a_party_profile_or_change_progression(self):
        inventory = Inventory()
        lattice = AetherLattice()
        abilities = CharacterAbilities(inventory, lattice)
        before = (inventory.to_dict(), lattice.to_dict(), abilities.to_dict())
        self.loadouts.reset()
        self.assertTrue(self.loadouts.restore(self.loadouts.to_dict()))
        self.assertEqual((inventory.to_dict(), lattice.to_dict(), abilities.to_dict()), before)
        self.assertNotIn('rivet', abilities.character_ids)
        self.assertNotIn('rivet', lattice.character_ids)
        self.assertEqual(abilities.character_ids, ('caelan', 'mira', 'lucan', 'rhea', 'edran'))

    def test_copies_and_round_trip_do_not_share_mutable_loadout_state(self):
        saved = self.loadouts.to_dict()
        other = BotLoadouts()
        for _ in range(2):
            self.assertTrue(other.restore(saved))
            self.assertEqual(other.to_dict(), saved)
        saved['loadouts']['mira']['ability_id'] = 'missing'
        result = other.battle_loadouts()
        result['mira']['bot_id'] = 'missing'
        self.assertEqual(other.battle_loadouts(), starting_battle_loadouts())
        self.assertFalse(other.restore(saved))
        self.assertEqual(other.battle_loadouts(), starting_battle_loadouts())

    def test_malformed_saves_are_rejected_atomically_without_extra_slots(self):
        saved = self.loadouts.to_dict()
        records = [None, True, [], {}, {'version': 1, 'loadouts': {}}]
        for field, value in (('version', True), ('version', 2), ('loadouts', [])):
            bad = deepcopy(saved);bad[field] = value;records.append(bad)
        bad = deepcopy(saved);bad['unexpected'] = True;records.append(bad)
        bad = deepcopy(saved);bad['loadouts']['caelan'] = bad['loadouts'].pop('mira');records.append(bad)
        bad = deepcopy(saved);bad['loadouts']['lucan'] = deepcopy(bad['loadouts']['mira']);records.append(bad)
        for field, value in (('bot_id', None), ('bot_id', []), ('bot_id', 'missing'),
                             ('ability_id', None), ('ability_id', []),
                             ('ability_id', 'missing'), ('ability_id', 'overclock')):
            bad = deepcopy(saved);bad['loadouts']['mira'][field] = value;records.append(bad)
        bad = deepcopy(saved);bad['loadouts']['mira']['ability_ids'] = ['piston_jab'];records.append(bad)
        for record in records:
            with self.subTest(record=record):
                self.assertFalse(self.loadouts.restore(record))
                self.assertEqual(self.loadouts.to_dict(), saved)

    def test_future_catalog_bots_are_not_granted_or_restored_as_owned(self):
        catalog = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
        catalog['bots']['fixture_future_bot'] = deepcopy(catalog['bots']['rivet'])
        catalog['bots']['fixture_foreign_bot'] = deepcopy(catalog['bots']['rivet'])
        catalog['bots']['fixture_foreign_bot']['owner_id'] = 'lucan'
        owner = BotLoadouts(catalog)
        self.assertEqual(owner.battle_loadouts(), starting_battle_loadouts())
        self.assertEqual(owner.owned_bots('mira'), frozenset({'rivet'}))
        self.assertEqual(owner.owned_bots('lucan'), frozenset())
        for bot_id in ('fixture_future_bot', 'fixture_foreign_bot'):
            bad = owner.to_dict();bad['loadouts']['mira']['bot_id'] = bot_id
            self.assertFalse(owner.restore(bad))
        self.assertEqual(owner.battle_loadouts(), starting_battle_loadouts())
        catalog['bots']['rivet']['ability_ids'].append('focused_strike')
        self.assertEqual(owner.definitions['rivet']['ability_ids'], ['piston_jab'])

    def test_valid_equipped_ability_can_round_trip_without_multiple_slots(self):
        definitions = load_bot_definitions()
        definitions['rivet']['ability_ids'].append('focused_strike')
        owner = BotLoadouts(definitions)
        saved = owner.to_dict();saved['loadouts']['mira']['ability_id'] = 'focused_strike'
        self.assertTrue(owner.restore(saved))
        self.assertEqual(owner.battle_loadouts()['mira']['ability_id'], 'focused_strike')
        owner.reset()
        self.assertEqual(owner.battle_loadouts()['mira']['ability_id'], 'piston_jab')

    def test_legacy_journeys_gain_only_defaults_and_explicit_null_is_invalid(self):
        self.assertTrue(BotLoadouts.valid_journey({}))
        self.assertTrue(BotLoadouts.valid_journey({'bot_loadouts': self.loadouts.to_dict()}))
        for record in (None, True, [], {}):
            self.assertFalse(BotLoadouts.valid_journey({'bot_loadouts': record}))
        for journey in (None, True, []):
            self.assertFalse(BotLoadouts.valid_journey(journey))

    def test_existing_caelan_equipment_history_remains_compatible(self):
        catalog = Inventory().catalog
        catalog['items']['fixture_blade'] = {
            'name': 'Fixture Blade', 'description': 'An equipment history fixture.',
            'category': 'weapons'}
        inventory = Inventory(catalog)
        abilities = CharacterAbilities(inventory, AetherLattice())
        self.assertTrue(abilities.acquire_weapon('caelan', 'fixture_blade'))
        self.assertTrue(abilities.equip_weapon('caelan', None))
        saved = abilities.to_dict()
        self.assertEqual(abilities.known_abilities(), frozenset({'basic_magicks', 'aether_edge'}))
        self.assertEqual(abilities.skill_ids(), ('aether_edge',))
        restored = CharacterAbilities(inventory, AetherLattice())
        self.assertTrue(restored.restore(saved))
        self.assertEqual(restored.to_dict(), saved)
        self.assertIn('aether_edge', restored.known_abilities())
        self.assertFalse(restored.has_weapon())
        restored.restore(None)
        self.assertEqual(restored.known_abilities(), frozenset({'basic_magicks'}))
        self.assertEqual(restored.known_abilities('mira'), frozenset({'rivet', 'overclock'}))

    def test_catalog_validation_rejects_resources_unknown_owners_and_invalid_abilities(self):
        catalog = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
        invalid = []
        for field, value in (('version', True), ('version', 2), ('bots', []), ('bots', {})):
            bad = deepcopy(catalog);bad[field] = value;invalid.append(bad)
        for field, value in (('owner_id', 'missing'), ('owner_id', []), ('name', ' '),
                             ('ability_id', 'overclock'), ('ability_ids', []),
                             ('ability_ids', ['piston_jab', 'piston_jab']),
                             ('ability_ids', [['piston_jab']]), ('ability_ids', ['missing']),
                             ('ability_ids', ['rivet'])):
            bad = deepcopy(catalog);bad['bots']['rivet'][field] = value;invalid.append(bad)
        for key, value in (('hp', 100), ('mp', 20), ('speed', True), ('str', -1), ('acc', 256)):
            bad = deepcopy(catalog);bad['bots']['rivet']['attributes'][key] = value;invalid.append(bad)
        for record in invalid:
            with self.subTest(record=record):
                before = deepcopy(record)
                with self.assertRaises(ValueError):load_bot_definitions(record)
                self.assertEqual(record, before)


if __name__ == '__main__':unittest.main()
