"""Gameplay caps constrain effective growth without losing its canonical owner."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

from aether_lattice import AetherLattice, LatticeBoard, MAX_RP
from character_attributes import (ATTRIBUTE_IDS, ATTRIBUTE_CAPS, MAX_ATTRIBUTE_VALUE,
                                  CharacterAttributes)
from inventory import Inventory
from lattice_progression import LatticeProgression


EXPECTED_CAPS = {key: 9999 if key == 'hp' else 999 if key == 'mp' else 255
                 for key in ATTRIBUTE_IDS}


class AttributeCapTests(unittest.TestCase):
    def setUp(self):
        self.attributes = CharacterAttributes()

    def state(self, attributes=None):
        attributes = attributes or self.attributes
        return (attributes.to_dict(),
                {key: attributes.value(key) for key in ATTRIBUTE_IDS})

    def test_all_eleven_caps_and_lookup_match_the_approved_limits(self):
        self.assertEqual(dict(ATTRIBUTE_CAPS), EXPECTED_CAPS)
        for key, maximum in EXPECTED_CAPS.items():
            with self.subTest(attribute=key):
                self.assertEqual(CharacterAttributes.cap(key), maximum)
        with self.assertRaises(KeyError):CharacterAttributes.cap('intelligence')

    def test_saved_base_accepts_each_cap_and_rejects_one_over_atomically(self):
        for key, maximum in EXPECTED_CAPS.items():
            with self.subTest(attribute=key):
                attributes = CharacterAttributes()
                record = attributes.to_dict()
                record['attributes'][key] = maximum
                self.assertTrue(attributes.restore(record))
                self.assertEqual(attributes.value(key), maximum)
                before = self.state(attributes)
                record['attributes'][key] = maximum+1
                self.assertFalse(CharacterAttributes.valid_snapshot(record))
                self.assertFalse(attributes.restore(record))
                self.assertEqual(self.state(attributes), before)

    def test_catalogs_reject_over_cap_profiles_without_mutating_them(self):
        for key, maximum in EXPECTED_CAPS.items():
            with self.subTest(attribute=key):
                catalog = deepcopy(self.attributes.catalog)
                catalog['characters']['caelan']['attributes'][key] = maximum
                self.assertEqual(CharacterAttributes(catalog=catalog).value(key), maximum)
                catalog['characters']['caelan']['attributes'][key] += 1
                original = deepcopy(catalog)
                with self.assertRaises(ValueError):CharacterAttributes(catalog=catalog)
                self.assertEqual(catalog, original)

    def test_effective_growth_stops_at_each_cap_without_refilling_resources(self):
        for key, maximum in EXPECTED_CAPS.items():
            with self.subTest(attribute=key):
                attributes = CharacterAttributes()
                base = attributes.base_value(key)
                before = attributes.to_dict()
                self.assertTrue(attributes.set_modifiers('lattice', {key: maximum-base-1}))
                self.assertEqual(attributes.value(key), maximum-1)
                self.assertTrue(attributes.set_modifiers('equipment', {key: 4}))
                self.assertEqual(attributes.value(key), maximum)
                self.assertEqual(attributes.base_value(key), base)
                self.assertEqual(attributes.to_dict(), before)
                self.assertEqual((attributes.current_hp, attributes.current_mp), (140, 30))

    def test_modifier_replacement_retains_growth_hidden_by_the_cap(self):
        self.assertTrue(self.attributes.set_modifiers('lattice', {'mag': 200}))
        self.assertTrue(self.attributes.set_modifiers('equipment', {'mag': 100}))
        self.assertEqual(self.attributes.value('mag'), 255)
        self.assertTrue(self.attributes.set_modifiers('lattice', {'mag': 20}))
        self.assertEqual(self.attributes.value('mag'), 130)
        self.assertEqual(self.attributes.base_value('mag'), 10)
        self.assertTrue(self.attributes.set_modifiers('equipment', {}))
        self.assertEqual(self.attributes.value('mag'), 30)

    def test_current_resources_cannot_exceed_their_capped_maxima(self):
        self.assertTrue(self.attributes.set_modifiers('lattice', {'hp': 20000, 'mp': 2000}))
        self.assertTrue(self.attributes.set_current(hp=9999, mp=999))
        before = self.state()
        for update in ({'hp': 10000}, {'mp': 1000}, {'hp': 10000, 'mp': 0},
                       {'hp': 0, 'mp': 1000}):
            with self.subTest(update=update):
                self.assertFalse(self.attributes.set_current(**update))
                self.assertEqual(self.state(), before)
        self.assertFalse(self.attributes.set_modifiers('lattice', {}))
        self.assertEqual(self.state(), before)

    def test_raw_storage_overflow_is_rejected_even_when_effective_value_is_capped(self):
        self.assertTrue(self.attributes.set_modifiers('lattice', {'str': MAX_ATTRIBUTE_VALUE-10}))
        self.assertEqual(self.attributes.value('str'), 255)
        before = self.state()
        self.assertFalse(self.attributes.set_modifiers('equipment', {'str': 1}))
        self.assertEqual(self.state(), before)
        self.assertFalse(self.attributes.set_modifiers('lattice', {'str': MAX_ATTRIBUTE_VALUE}))
        self.assertEqual(self.state(), before)

    def test_capped_canonical_bonuses_restore_idempotently_without_changing_base(self):
        bonuses = {'hp': 20000, 'mp': 2000, 'str': 400, 'mag': 500}
        self.assertTrue(self.attributes.set_modifiers('lattice', bonuses))
        self.assertTrue(self.attributes.set_current(hp=9999, mp=999))
        record, expected = self.attributes.to_dict(), self.state()
        self.assertTrue(CharacterAttributes.valid_snapshot(record, lattice_bonuses=bonuses))
        clone = CharacterAttributes()
        for _ in range(3):
            self.assertTrue(clone.restore(record, lattice_bonuses=bonuses))
            self.assertEqual(self.state(clone), expected)
            self.assertEqual(clone.base_value('hp'), 140)
            self.assertEqual(clone.base_value('str'), 10)
        for resource, invalid in (('hp', 10000), ('mp', 1000)):
            bad = deepcopy(record);bad['current_'+resource] = invalid
            self.assertFalse(clone.restore(bad, lattice_bonuses=bonuses))
            self.assertEqual(self.state(clone), expected)

    def test_every_saved_format_rejects_over_cap_base_values(self):
        for version in (1, 2, 3):
            for key, maximum in EXPECTED_CAPS.items():
                with self.subTest(version=version, attribute=key):
                    record = self.attributes.to_dict();record['version'] = version
                    record['attributes'][key] = maximum+1
                    before = self.state()
                    self.assertFalse(self.attributes.restore(record))
                    self.assertEqual(self.state(), before)

    def fixture(self, stat, base, amount):
        data = deepcopy(LatticeBoard().data)
        data['id'] = 'cap_fixture_'+stat
        crystal = ('aether_emerald' if stat == 'hp' else
                   'aether_sapphire' if stat == 'mp' else 'aether_ruby')
        for identifier in ('hp_01', 'hp_02'):
            data['nodes'][identifier].update(stat=stat, amount=amount, cost={crystal: 1})
        board = LatticeBoard(data)
        lattice, inventory, attributes = AetherLattice(board), Inventory(), CharacterAttributes()
        record = attributes.to_dict();record['attributes'][stat] = base
        self.assertTrue(attributes.restore(record))
        self.assertTrue(attributes.set_current(hp=attributes.value('hp'), mp=attributes.value('mp')))
        progression = LatticeProgression(lattice, inventory, {'caelan': attributes})
        self.assertTrue(progression.award_battle_rewards('cap:fixture', {'caelan': MAX_RP}, {crystal: 2}))
        self.assertTrue(progression.move('hp_01'))
        return board, lattice, inventory, attributes, progression, crystal

    def test_lattice_crossing_each_cap_earns_remaining_room_and_keeps_canonical_bonus(self):
        for stat in ATTRIBUTE_IDS:
            base, amount = ((9950, 100) if stat == 'hp' else
                            (990, 30) if stat == 'mp' else (254, 4))
            with self.subTest(attribute=stat):
                board, lattice, inventory, attributes, progression, crystal = self.fixture(stat, base, amount)
                current = attributes.current_hp, attributes.current_mp
                self.assertEqual(progression.activation_reason('hp_01'), '')
                self.assertTrue(progression.activate('hp_01'))
                self.assertEqual(attributes.value(stat), EXPECTED_CAPS[stat])
                self.assertEqual(attributes.base_value(stat), base)
                self.assertEqual(lattice.bonuses()[stat], amount)
                self.assertEqual(inventory.quantity(crystal), 1)
                self.assertEqual((attributes.current_hp, attributes.current_mp), current)
                saved_lattice, saved_attributes = lattice.to_dict(), attributes.to_dict()
                for _ in range(2):
                    clone = AetherLattice(board)
                    self.assertTrue(clone.restore(saved_lattice))
                    restored = CharacterAttributes()
                    self.assertTrue(restored.restore(saved_attributes, lattice_bonuses=clone.bonuses()))
                    self.assertEqual(restored.value(stat), EXPECTED_CAPS[stat])
                    self.assertEqual(clone.bonuses()[stat], amount)
                self.assertTrue(progression.move('hp_02'))
                before = lattice.to_dict(), inventory.to_dict(), self.state(attributes)
                self.assertTrue(progression.activation_reason('hp_02'))
                self.assertFalse(progression.activate('hp_02'))
                self.assertEqual((lattice.to_dict(), inventory.to_dict(), self.state(attributes)), before)

    def test_real_continue_rebuilds_over_cap_lattice_growth_without_stacking(self):
        import pygame
        from main import Game
        with tempfile.TemporaryDirectory(prefix='attribute-cap-continue-') as directory:
            root = Path(directory)
            path, settings = root/'journey.json', root/'settings.json'
            self.addCleanup(pygame.quit)
            game = Game(fullscreen=False, start_on_title=False, save_path=path, settings_path=settings)
            game.audio.set_music(0);game.audio.set_effects(0)
            record = game.attributes.to_dict()
            record['attributes']['hp'] = 9950;record['current_hp'] = 9950
            self.assertTrue(game.attributes.restore(record))
            self.assertTrue(game.award_battle_rewards('cap:real', {'caelan': 20}, {'aether_emerald': 1}))
            self.assertTrue(game.move_lattice('hp_01'))
            self.assertTrue(game.activate_lattice('hp_01'))
            self.assertEqual(game.attributes.value('hp'), 9999)
            self.assertEqual(game.attributes.current_hp, 9950)
            self.assertTrue(game.attributes.set_current(hp=9999))
            self.assertTrue(game.save_progress())
            saved = path.read_bytes()
            self.assertTrue(LatticeProgression.valid_journey(json.loads(saved)))
            for _ in range(2):
                restored = Game(fullscreen=False, start_on_title=True,
                                save_path=path, settings_path=settings)
                self.assertTrue(restored.has_saved_journey)
                self.assertEqual(path.read_bytes(), saved)
                self.assertTrue(restored.begin_journey(True))
                self.assertEqual(restored.attributes.base_value('hp'), 9950)
                self.assertEqual(restored.attributes.value('hp'), 9999)
                self.assertEqual(restored.attributes.current_hp, 9999)
                self.assertEqual(restored.lattice.bonuses()['hp'], 100)
                self.assertEqual(restored.inventory.quantity('aether_emerald'), 0)
                self.assertEqual(restored.lattice.steps(), 0)
                self.assertTrue(restored.save_progress())
                self.assertEqual(json.loads(path.read_bytes())['character_attributes'],
                                 json.loads(saved)['character_attributes'])
                self.assertEqual(json.loads(path.read_bytes())['aether_lattice'],
                                 json.loads(saved)['aether_lattice'])


if __name__ == '__main__':unittest.main()
