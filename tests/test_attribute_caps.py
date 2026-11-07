"""Gameplay caps constrain effective growth without losing its canonical owner."""
from copy import deepcopy
import json
import os
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

from character_attributes import (ATTRIBUTE_IDS, ATTRIBUTE_CAPS, MAX_ATTRIBUTE_VALUE,
                                  CharacterAttributes)


EXPECTED_CAPS = {key: 9999 if key == 'hp' else 255 if key == 'speed' else 999
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
                self.assertTrue(attributes.set_modifiers('permanent', {key: maximum-base-1}))
                self.assertEqual(attributes.value(key), maximum-1)
                self.assertTrue(attributes.set_modifiers('equipment', {key: 4}))
                self.assertEqual(attributes.value(key), maximum)
                self.assertEqual(attributes.base_value(key), base)
                self.assertEqual(attributes.to_dict(), before)
                self.assertEqual((attributes.current_hp, attributes.current_mp), (140, 30))

    def test_modifier_replacement_retains_growth_hidden_by_the_cap(self):
        self.assertTrue(self.attributes.set_modifiers('permanent', {'mag': 900}))
        self.assertTrue(self.attributes.set_modifiers('equipment', {'mag': 100}))
        self.assertEqual(self.attributes.value('mag'), 999)
        self.assertTrue(self.attributes.set_modifiers('permanent', {'mag': 20}))
        self.assertEqual(self.attributes.value('mag'), 130)
        self.assertEqual(self.attributes.base_value('mag'), 10)
        self.assertTrue(self.attributes.set_modifiers('equipment', {}))
        self.assertEqual(self.attributes.value('mag'), 30)

    def test_current_resources_cannot_exceed_their_capped_maxima(self):
        self.assertTrue(self.attributes.set_modifiers('permanent', {'hp': 20000, 'mp': 2000}))
        self.assertTrue(self.attributes.set_current(hp=9999, mp=999))
        before = self.state()
        for update in ({'hp': 10000}, {'mp': 1000}, {'hp': 10000, 'mp': 0},
                       {'hp': 0, 'mp': 1000}):
            with self.subTest(update=update):
                self.assertFalse(self.attributes.set_current(**update))
                self.assertEqual(self.state(), before)
        self.assertFalse(self.attributes.set_modifiers('permanent', {}))
        self.assertEqual(self.state(), before)

    def test_raw_storage_overflow_is_rejected_even_when_effective_value_is_capped(self):
        self.assertTrue(self.attributes.set_modifiers('permanent', {'str': MAX_ATTRIBUTE_VALUE-10}))
        self.assertEqual(self.attributes.value('str'), 999)
        before = self.state()
        self.assertFalse(self.attributes.set_modifiers('equipment', {'str': 1}))
        self.assertEqual(self.state(), before)
        self.assertFalse(self.attributes.set_modifiers('permanent', {'str': MAX_ATTRIBUTE_VALUE}))
        self.assertEqual(self.state(), before)

    def test_capped_canonical_bonuses_restore_idempotently_without_changing_base(self):
        bonuses = {'hp': 20000, 'mp': 2000, 'str': 400, 'mag': 500}
        self.assertTrue(self.attributes.set_modifiers('permanent', bonuses))
        self.assertTrue(self.attributes.set_current(hp=9999, mp=999))
        record, expected = self.attributes.to_dict(), self.state()
        self.assertTrue(CharacterAttributes.valid_snapshot(record, modifier_bonuses=bonuses))
        clone = CharacterAttributes()
        for _ in range(3):
            self.assertTrue(clone.restore(record, modifier_bonuses=bonuses))
            self.assertEqual(self.state(clone), expected)
            self.assertEqual(clone.base_value('hp'), 140)
            self.assertEqual(clone.base_value('str'), 10)
        for resource, invalid in (('hp', 10000), ('mp', 1000)):
            bad = deepcopy(record);bad['current_'+resource] = invalid
            self.assertFalse(clone.restore(bad, modifier_bonuses=bonuses))
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

    def test_legacy_ratings_restore_without_rescaling_and_new_ratings_round_trip(self):
        for version in (1, 2, 3):
            for rating in (255, 999):
                with self.subTest(version=version, rating=rating):
                    record = self.attributes.to_dict()
                    record['version'] = version
                    record['attributes'].update({key: rating for key in ATTRIBUTE_IDS
                                                 if key not in ('hp', 'mp', 'speed')})
                    record['attributes']['speed'] = 255
                    record.update(current_hp=37, current_mp=4)
                    self.assertTrue(self.attributes.restore(record))
                    expected = {**record, 'version': 3}
                    self.assertEqual(self.attributes.to_dict(), expected)
                    clone = CharacterAttributes()
                    self.assertTrue(clone.restore(expected))
                    self.assertEqual(self.state(clone), self.state())

    def test_battle_catalogs_and_party_snapshots_share_the_new_rating_caps(self):
        from battle_model import (BOT_PATH, ENEMY_PATH, GUEST_PATH, BattleModel,
                                  load_actions, load_bots, load_enemies, load_guests)
        actions = load_actions()
        ratings = {key: EXPECTED_CAPS[key] for key in ATTRIBUTE_IDS
                   if key not in ('hp', 'mp')}
        for path, group, identifier, loader in (
                (ENEMY_PATH, 'enemies', 'bat', load_enemies),
                (GUEST_PATH, 'guests', 'mira', load_guests),
                (BOT_PATH, 'bots', 'rivet', load_bots)):
            data = json.loads(path.read_text())
            data[group][identifier]['attributes'].update(ratings)
            if group == 'enemies':
                data[group][identifier]['attributes'].update(hp=50000, mp=10000)
            parsed = loader(actions, data)
            for key, cap in ratings.items():
                with self.subTest(catalog=group, attribute=key):
                    self.assertEqual(parsed[identifier]['attributes'][key], cap)
                    bad = deepcopy(data)
                    bad[group][identifier]['attributes'][key] = cap+1
                    with self.assertRaises(ValueError):loader(actions, bad)
        member = {'identifier': 'player', 'name': 'Caelan', 'attributes': dict(EXPECTED_CAPS),
                  'hp': 37, 'mp': 4, 'attack': 'attack'}
        model = BattleModel(CharacterAttributes(), party_members=[member])
        self.assertEqual(model.player.attributes, EXPECTED_CAPS)
        self.assertEqual((model.player.hp, model.player.mp), (37, 4))
        for key, cap in ratings.items():
            with self.subTest(party_attribute=key):
                bad = deepcopy(member)
                bad['attributes'][key] = cap+1
                with self.assertRaises(ValueError):
                    BattleModel(CharacterAttributes(), party_members=[bad])





if __name__ == '__main__':unittest.main()
