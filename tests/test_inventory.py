"""Ownership, protected key items and atomic, replay-safe quest handoffs."""
from copy import deepcopy
import unittest

from inventory import Inventory, MAX_QUANTITY


def expanded_catalog():
    catalog = Inventory().catalog
    for identifier, category in (('sword', 'weapons'), ('coat', 'armor'), ('tonic', 'items')):
        catalog['items'][identifier] = {'name': identifier.title(), 'category': category,
                                       'description': 'A test item for ownership checks.'}
    return catalog


class InventoryTests(unittest.TestCase):
    def test_all_categories_can_hold_items_and_duplicate_equipment(self):
        inv = Inventory(expanded_catalog())
        for key in ('sword', 'coat', 'tonic', 'halden_medicine'):
            self.assertTrue(inv.add(key, 2))
            self.assertEqual(inv.quantity(key), 2)
        for category in ('weapons', 'armor', 'items', 'key_items'):
            self.assertEqual(len(inv.entries(category)), 1)
        self.assertTrue(inv.remove('sword'))
        self.assertTrue(inv.remove('tonic', 2))
        self.assertEqual(inv.entries('items'), [])
        self.assertFalse(inv.remove('halden_medicine'))
        self.assertEqual(inv.quantity('halden_medicine'), 2)

    def test_bad_quantities_unknown_items_and_overflow_do_not_mutate(self):
        inv = Inventory(expanded_catalog())
        inv.add('tonic', 5)
        before = inv.to_dict()
        for quantity in (True, False, 0, -1, 1.5, '2', MAX_QUANTITY+1):
            self.assertFalse(inv.add('tonic', quantity))
            self.assertFalse(inv.remove('tonic', quantity))
            self.assertEqual(inv.to_dict(), before)
        self.assertFalse(inv.add_many({'tonic': 1, 'unknown': 1}))
        self.assertFalse(inv.remove('tonic', 6))
        self.assertEqual(inv.to_dict(), before)

    def test_supply_grants_are_exactly_once(self):
        inv = Inventory()
        self.assertTrue(inv.grant_quest('CH01_MQ01'))
        self.assertFalse(inv.grant_quest('CH01_MQ01'))
        self.assertFalse(inv.grant_quest('unknown'))
        self.assertEqual({item['quantity'] for item in inv.entries()}, {1})
        self.assertEqual(len(inv.entries()), 3)

    def test_delivery_is_protected_recipient_checked_and_idempotent(self):
        inv = Inventory()
        inv.grant_quest('CH01_MQ01')
        before = inv.to_dict()
        self.assertFalse(inv.deliver('CH01_MQ01', 'halden', 'elira'))
        self.assertFalse(inv.deliver('CH01_MQ01', 'missing', 'halden'))
        self.assertEqual(inv.to_dict(), before)
        self.assertTrue(inv.deliver('CH01_MQ01', 'halden', 'halden'))
        self.assertEqual(inv.quantity('halden_medicine'), 0)
        self.assertEqual(inv.quantity('elira_supplies'), 1)
        self.assertTrue(inv.was_delivered('CH01_MQ01', 'halden'))
        self.assertFalse(inv.deliver('CH01_MQ01', 'halden', 'halden'))
        restored = Inventory()
        self.assertTrue(restored.restore(inv.to_dict()))
        self.assertFalse(restored.grant_quest('CH01_MQ01'))
        self.assertFalse(restored.deliver('CH01_MQ01', 'halden', 'halden'))
        self.assertEqual(restored.quantity('halden_medicine'), 0)

    def test_missing_bundle_does_not_record_delivery(self):
        inv = Inventory()
        inv.grant_quest('CH01_MQ01')
        payload = inv.to_dict()
        payload['items'].pop('halden_medicine')
        self.assertTrue(inv.restore(payload))
        before = inv.to_dict()
        self.assertFalse(inv.deliver('CH01_MQ01', 'halden', 'halden'))
        self.assertEqual(inv.to_dict(), before)

    def test_malformed_saves_are_rejected_without_partial_restore(self):
        inv = Inventory()
        inv.grant_quest('CH01_MQ01')
        before = inv.to_dict()
        bad = []
        for value in (True, 0, -1, MAX_QUANTITY+1, 'one'):
            payload = deepcopy(before)
            payload['items']['halden_medicine'] = value
            bad.append(payload)
        for field, value in (('version', True), ('items', {'missing': 1}),
                             ('granted_quests', ['unknown']), ('deliveries', ['unknown']),
                             ('granted_quests', ['CH01_MQ01', 'CH01_MQ01'])):
            payload = deepcopy(before)
            payload[field] = value
            bad.append(payload)
        payload = deepcopy(before)
        payload.update(granted_quests=[], deliveries=['CH01_MQ01/halden'])
        bad.append(payload)
        for payload in bad:
            self.assertFalse(inv.restore(payload))
            self.assertEqual(inv.to_dict(), before)

    def test_metadata_and_snapshots_cannot_mutate_ownership(self):
        inv = Inventory()
        inv.grant_quest('CH01_MQ01')
        snapshot = inv.to_dict()
        snapshot['items'].clear()
        entry = inv.entries()[0]
        entry['name'] = 'Changed'
        self.assertEqual(len(inv.entries()), 3)
        self.assertNotEqual(inv.entries()[0]['name'], 'Changed')

    def test_invalid_category_fails_catalog_validation(self):
        catalog = expanded_catalog()
        catalog['items']['sword']['category'] = 'invalid'
        with self.assertRaises(ValueError):Inventory(catalog)


if __name__ == '__main__':unittest.main()
