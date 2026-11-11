"""Retired bot ownership is empty while retained legacy catalogue data stays strict."""
from copy import deepcopy
import json
import unittest

from bot_loadouts import (BotLoadouts, CATALOG_PATH, load_bot_definitions,
                          starting_battle_loadouts)
from character_abilities import CharacterAbilities, starting_abilities
from inventory import Inventory


RIG_SKILLS = ('charged_bolt', 'bulwark', 'repair_pulse', 'impact_bolt', 'arc_discharge')
RIG_STARTERS = frozenset({'arm_rig', *RIG_SKILLS})


class BotLoadoutsTests(unittest.TestCase):
    def setUp(self):self.loadouts = BotLoadouts()

    def test_starting_registry_grants_a_worn_rig_and_no_owned_autonomous_attachment(self):
        self.assertEqual(self.loadouts.battle_loadouts(), {})
        self.assertEqual(starting_battle_loadouts(), {})
        for owner in ('mira', 'caelan', 'lucan', 'rhea', 'edran', 'missing', [], None):
            self.assertEqual(self.loadouts.owned_bots(owner), frozenset())
        self.assertEqual(starting_abilities('mira'), RIG_STARTERS)
        self.assertEqual(starting_abilities('caelan'), frozenset({'basic_magicks'}))
        self.assertEqual(starting_abilities('missing'), frozenset())

    def test_rig_capability_and_techniques_are_miras_without_retired_commands(self):
        abilities = CharacterAbilities(Inventory())
        self.assertEqual(abilities.known_abilities('mira'), RIG_STARTERS)
        self.assertEqual(abilities.skill_ids('mira'), RIG_SKILLS)
        self.assertEqual(abilities.definitions['arm_rig']['kind'], 'capability')
        for identifier in ('rivet', 'overclock', 'piston_jab', 'deploy_rivet', 'repair_rivet'):
            self.assertNotIn(identifier, abilities.known_abilities('mira'))
            self.assertNotIn(identifier, abilities.skill_ids('mira'))

    def test_reset_does_not_create_a_party_profile_or_change_progression(self):
        inventory = Inventory();abilities = CharacterAbilities(inventory)
        before = (inventory.to_dict(), abilities.to_dict())
        self.loadouts.reset()
        self.assertTrue(self.loadouts.restore(self.loadouts.to_dict()))
        self.assertEqual((inventory.to_dict(), abilities.to_dict()), before)
        self.assertNotIn('rivet', abilities.character_ids)
        self.assertEqual(abilities.character_ids, ('caelan', 'mira', 'lucan', 'rhea', 'edran'))

    def test_empty_modern_state_round_trips_without_sharing_mutable_ownership(self):
        saved = self.loadouts.to_dict();other = BotLoadouts()
        self.assertEqual(saved, {'version': 1, 'loadouts': {}})
        for _ in range(2):
            self.assertTrue(other.restore(saved))
            self.assertEqual(other.to_dict(), saved)
        saved['loadouts']['mira'] = {'bot_id': 'rivet', 'ability_id': 'piston_jab'}
        self.assertFalse(other.restore(saved))
        self.assertEqual(other.battle_loadouts(), {})
        returned = other.battle_loadouts();returned['mira'] = {'bot_id': 'rivet'}
        self.assertEqual(other.battle_loadouts(), {})

    def test_malformed_modern_state_is_rejected_atomically(self):
        saved = self.loadouts.to_dict()
        invalid = [None, True, [], {}, {'version': True, 'loadouts': {}},
                   {'version': 2, 'loadouts': {}}, {'version': 1, 'loadouts': []},
                   {'version': 1, 'loadouts': {}, 'unexpected': True},
                   {'version': 1, 'loadouts': {'lucan': {'bot_id': 'rivet', 'ability_id': 'piston_jab'}}},
                   {'version': 1, 'loadouts': {'mira': {'bot_id': 'missing', 'ability_id': 'piston_jab'}}}]
        for record in invalid:
            with self.subTest(record=record):
                self.assertFalse(self.loadouts.restore(record))
                self.assertEqual(self.loadouts.to_dict(), saved)

    def test_future_catalogue_entries_do_not_grant_or_restore_ownership(self):
        catalog = json.loads(CATALOG_PATH.read_text())
        catalog['bots']['fixture_future_bot'] = deepcopy(catalog['bots']['rivet'])
        catalog['bots']['fixture_foreign_bot'] = deepcopy(catalog['bots']['rivet'])
        catalog['bots']['fixture_foreign_bot']['owner_id'] = 'lucan'
        owner = BotLoadouts(catalog)
        self.assertEqual(owner.battle_loadouts(), {})
        self.assertEqual(owner.owned_bots('mira'), frozenset())
        self.assertEqual(owner.owned_bots('lucan'), frozenset())
        for bot_id in ('rivet', 'fixture_future_bot', 'fixture_foreign_bot'):
            self.assertFalse(owner.restore({'version': 1, 'loadouts': {
                'mira': {'bot_id': bot_id, 'ability_id': 'piston_jab'}}}))
        catalog['bots']['rivet']['ability_ids'].append('focused_strike')
        self.assertEqual(owner.definitions['rivet']['ability_ids'], ['piston_jab'])

    def test_valid_catalogue_ability_does_not_reintroduce_an_equipped_bot(self):
        definitions = load_bot_definitions()
        definitions['rivet']['ability_ids'].append('focused_strike')
        owner = BotLoadouts(definitions)
        self.assertFalse(owner.restore({'version': 1, 'loadouts': {
            'mira': {'bot_id': 'rivet', 'ability_id': 'focused_strike'}}}))
        owner.reset();self.assertEqual(owner.battle_loadouts(), {})

    def test_modern_journey_shape_defaults_to_empty_and_rejects_explicit_null(self):
        self.assertTrue(BotLoadouts.valid_journey({}))
        self.assertTrue(BotLoadouts.valid_journey({'bot_loadouts': self.loadouts.to_dict()}))
        for record in (None, True, [], {}):
            self.assertFalse(BotLoadouts.valid_journey({'bot_loadouts': record}))
        for journey in (None, True, []):self.assertFalse(BotLoadouts.valid_journey(journey))

    def test_existing_caelan_equipment_history_remains_compatible(self):
        catalog = Inventory().catalog
        catalog['items']['fixture_blade'] = {
            'name': 'Fixture Blade', 'description': 'An equipment history fixture.', 'category': 'weapons'}
        inventory = Inventory(catalog);abilities = CharacterAbilities(inventory)
        self.assertTrue(abilities.acquire_weapon('caelan', 'fixture_blade'))
        self.assertTrue(abilities.equip_weapon('caelan', None))
        saved = abilities.to_dict()
        restored = CharacterAbilities(inventory)
        self.assertTrue(restored.restore(saved));self.assertEqual(restored.to_dict(), saved)
        self.assertIn('aether_edge', restored.known_abilities());self.assertFalse(restored.has_weapon())
        restored.restore(None)
        self.assertEqual(restored.known_abilities(), frozenset({'basic_magicks'}))
        self.assertEqual(restored.known_abilities('mira'), RIG_STARTERS)

    def test_retained_catalogue_validation_rejects_invalid_owners_attributes_and_abilities(self):
        catalog = json.loads(CATALOG_PATH.read_text())
        invalid = []
        for field, value in (('version', True), ('version', 2), ('bots', []), ('bots', {})):
            bad = deepcopy(catalog);bad[field] = value;invalid.append(bad)
        for field, value in (('owner_id', 'missing'), ('owner_id', []), ('name', ' '),
                             ('ability_id', 'overclock'), ('ability_ids', []),
                             ('ability_ids', ['piston_jab', 'piston_jab']),
                             ('ability_ids', [['piston_jab']]), ('ability_ids', ['missing']),
                             ('ability_ids', ['rivet'])):
            bad = deepcopy(catalog);bad['bots']['rivet'][field] = value;invalid.append(bad)
        for key, value in (('hp', 100), ('mp', 20), ('speed', True), ('speed', 256), ('str', -1), ('acc', 1000)):
            bad = deepcopy(catalog);bad['bots']['rivet']['attributes'][key] = value;invalid.append(bad)
        for record in invalid:
            with self.subTest(record=record):
                before = deepcopy(record)
                with self.assertRaises(ValueError):load_bot_definitions(record)
                self.assertEqual(record, before)


if __name__ == '__main__':unittest.main()
