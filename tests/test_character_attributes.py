"""The character foundation keeps ratings, resources and saved records distinct."""
from copy import deepcopy
import unittest

from character_attributes import ATTRIBUTE_IDS, MAX_ATTRIBUTE_VALUE, CharacterAttributes


class CharacterAttributeTests(unittest.TestCase):
    def setUp(self):
        self.attributes = CharacterAttributes('caelan')

    def test_balanced_caelan_profile_and_author_approved_labels(self):
        attributes = self.attributes
        self.assertEqual(attributes.character_id, 'caelan')
        self.assertEqual(attributes.name, 'Caelan')
        self.assertEqual([attributes.definitions[key]['label'] for key in ATTRIBUTE_IDS],
                         ['HP', 'MP', 'Str', 'Mag', 'Spr', 'Def', 'M. Def',
                          'Speed', 'Acc', 'Eva', 'Lck'])
        self.assertEqual([attributes.value(key) for key in ATTRIBUTE_IDS],
                         [140, 30, *([10]*9)])
        self.assertEqual((attributes.current_hp, attributes.current_mp), (140, 30))

    def test_metadata_separates_healing_damage_and_resource_capacity(self):
        definitions = self.attributes.definitions
        self.assertIn('damaging spells', definitions['mag']['description'])
        self.assertIn('healing spells', definitions['spr']['description'])
        self.assertIn('without increasing spell power', definitions['mp']['description'])
        for key in ('acc', 'eva', 'lck'):
            self.assertIn('not a', definitions[key]['description'])
            self.assertIn('percentage', definitions[key]['description'])
        self.assertIn('does not change exploration', definitions['speed']['description'])

    def test_resource_changes_leave_maxima_and_other_attributes_unchanged(self):
        before = self.attributes.to_dict()['attributes']
        self.assertTrue(self.attributes.set_current(hp=125, mp=7))
        self.assertEqual(self.attributes.to_dict()['attributes'], before)
        self.assertTrue(self.attributes.set_current(hp=0))
        self.assertEqual((self.attributes.current_hp, self.attributes.current_mp), (0, 7))
        self.assertTrue(self.attributes.set_current(mp=0))
        self.assertEqual((self.attributes.current_hp, self.attributes.current_mp), (0, 0))

    def test_invalid_resource_updates_are_atomic(self):
        self.assertTrue(self.attributes.set_current(hp=123, mp=8))
        before = self.attributes.to_dict()
        for bad in (-1, True, False, 1.0, '10', [], {}, MAX_ATTRIBUTE_VALUE+1):
            for field in ('hp', 'mp'):
                with self.subTest(field=field, bad=bad):
                    update = {'hp': 100, 'mp': 5, field: bad}
                    self.assertFalse(self.attributes.set_current(**update))
                    self.assertEqual(self.attributes.to_dict(), before)
        self.assertFalse(self.attributes.set_current(hp=141, mp=3))
        self.assertFalse(self.attributes.set_current(hp=10, mp=31))
        self.assertEqual(self.attributes.to_dict(), before)

    def test_round_trip_restores_all_ratings_and_depleted_resources(self):
        data = self.attributes.to_dict()
        data['attributes'].update(hp=450, mp=0, str=18, mag=14, spr=22,
                                  acc=17, eva=16, lck=15)
        data.update(current_hp=211, current_mp=0)
        self.assertTrue(CharacterAttributes.valid_snapshot(data))
        self.assertTrue(self.attributes.restore(data))
        self.assertEqual(self.attributes.to_dict(), data)
        other = CharacterAttributes()
        self.assertTrue(other.restore(self.attributes.to_dict()))
        self.assertEqual(other.to_dict(), data)
        data['attributes']['spr'] = 999
        self.assertEqual(other.value('spr'), 22)

    def test_instances_exports_and_reset_are_independent(self):
        before = self.attributes.to_dict()
        other = CharacterAttributes()
        exported = self.attributes.to_dict()
        exported['attributes']['str'] = 99
        self.assertEqual(self.attributes.value('str'), 10)
        self.assertTrue(self.attributes.restore(exported))
        self.assertTrue(self.attributes.set_current(hp=3, mp=1))
        self.assertEqual(other.to_dict(), before)
        self.attributes.definitions['spr']['name'] = 'Changed'
        self.assertEqual(other.definitions['spr']['name'], 'Spirit')
        self.attributes.reset()
        self.assertEqual(self.attributes.to_dict(), before)

    def test_invalid_snapshot_shapes_and_versions_never_mutate(self):
        self.assertTrue(self.attributes.set_current(hp=83, mp=4))
        before = self.attributes.to_dict()
        records = [None, [], {}, True]
        for field in before:
            missing = deepcopy(before)
            missing.pop(field)
            records.append(missing)
        for value in (0, 3, True, 1.0, '1', None):
            records.append({**deepcopy(before), 'version': value})
        records.append({**deepcopy(before), 'extra': 1})
        for value in ('mira', '', None, 10, True, []):
            records.append({**deepcopy(before), 'character_id': value})
        for record in records:
            with self.subTest(record=record):
                self.assertFalse(CharacterAttributes.valid_snapshot(record))
                self.assertFalse(self.attributes.restore(record))
                self.assertEqual(self.attributes.to_dict(), before)

    def test_snapshot_attributes_and_resources_are_strict_and_bounded(self):
        before = self.attributes.to_dict()
        records = []
        for field in ATTRIBUTE_IDS:
            for bad in (-1, True, 1.0, '10', None, MAX_ATTRIBUTE_VALUE+1):
                record = deepcopy(before)
                record['attributes'][field] = bad
                records.append(record)
            missing = deepcopy(before)
            missing['attributes'].pop(field)
            records.append(missing)
        records.append({**deepcopy(before), 'attributes': []})
        record = deepcopy(before)
        record['attributes']['intelligence'] = 10
        records.append(record)
        record = deepcopy(before)
        record['attributes']['hp'] = 0
        records.append(record)
        for field in ('current_hp', 'current_mp'):
            for bad in (-1, True, 1.0, '10', None, MAX_ATTRIBUTE_VALUE+1):
                records.append({**deepcopy(before), field: bad})
        records.extend([{**deepcopy(before), 'current_hp': 141},
                        {**deepcopy(before), 'current_mp': 31}])
        for record in records:
            with self.subTest(record=record):
                self.assertFalse(CharacterAttributes.valid_snapshot(record))
                self.assertFalse(self.attributes.restore(record))
                self.assertEqual(self.attributes.to_dict(), before)
        maximum = deepcopy(before)
        maximum['attributes'] = dict.fromkeys(ATTRIBUTE_IDS, MAX_ATTRIBUTE_VALUE)
        maximum.update(current_hp=MAX_ATTRIBUTE_VALUE, current_mp=MAX_ATTRIBUTE_VALUE)
        self.assertTrue(self.attributes.restore(maximum))

    def test_original_caelan_health_migrates_once_and_preserves_other_ratings(self):
        for current, expected in ((0, 0), (1, 1), (150, 70), (213, 99), (300, 140)):
            with self.subTest(current=current):
                original = self.attributes.to_dict()
                original['version'] = 1
                original['attributes'].update(hp=300, mag=13, spr=17)
                original.update(current_hp=current, current_mp=9)
                untouched = deepcopy(original)
                self.assertTrue(CharacterAttributes.valid_snapshot(original))
                self.assertTrue(self.attributes.restore(original))
                self.assertEqual(self.attributes.value('hp'), 140)
                self.assertEqual(self.attributes.current_hp, expected)
                self.assertEqual(self.attributes.current_mp, 9)
                self.assertEqual(self.attributes.value('mag'), 13)
                self.assertEqual(self.attributes.value('spr'), 17)
                self.assertEqual(original, untouched)
                migrated = self.attributes.to_dict()
                self.assertEqual(migrated['version'], 2)
                self.assertTrue(self.attributes.restore(migrated))
                self.assertEqual(self.attributes.to_dict(), migrated)

    def test_saved_growth_and_version_two_300_hp_are_not_retuned(self):
        for version, maximum, current in ((1, 400, 213), (1, 140, 98), (2, 300, 213)):
            with self.subTest(version=version, maximum=maximum):
                data = self.attributes.to_dict()
                data.update(version=version, current_hp=current)
                data['attributes']['hp'] = maximum
                self.assertTrue(self.attributes.restore(data))
                self.assertEqual(self.attributes.value('hp'), maximum)
                self.assertEqual(self.attributes.current_hp, current)

    def test_catalog_errors_fail_early_and_do_not_change_input(self):
        catalog = deepcopy(self.attributes.catalog)
        records = [[], {}, {**catalog, 'version': True}]
        missing_spr = deepcopy(catalog)
        del missing_spr['attributes']['spr']
        records.append(missing_spr)
        malformed_description = deepcopy(catalog)
        malformed_description['attributes']['spr']['description'] = ''
        records.append(malformed_description)
        malformed_profile = deepcopy(catalog)
        malformed_profile['characters']['caelan']['attributes']['hp'] = False
        records.append(malformed_profile)
        for record in records:
            with self.subTest(record=record):
                before = deepcopy(record)
                with self.assertRaises(ValueError):
                    CharacterAttributes(catalog=record)
                self.assertEqual(record, before)
        with self.assertRaises(ValueError):
            CharacterAttributes('unknown')
        with self.assertRaises(KeyError):
            self.attributes.value('intelligence')
        clone = CharacterAttributes(catalog=catalog)
        clone.definitions['spr']['name'] = 'Changed'
        self.assertEqual(catalog['attributes']['spr']['name'], 'Spirit')


if __name__ == '__main__':
    unittest.main()
