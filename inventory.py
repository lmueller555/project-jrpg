"""Item ownership and idempotent quest handoffs, independent of presentation.

Definitions belong to the catalog, quantities to the journey. Identical items
are counted by stable ID; differing equipment stats can use distinct catalog
IDs. Equipment slots/combat effects are metadata for their future controllers.
"""
from copy import deepcopy
import json
from pathlib import Path


CATEGORIES = ('weapons', 'armor', 'items', 'key_items')
CATEGORY_NAMES = ('Weapons', 'Armor', 'Items', 'Key Items')
MAX_QUANTITY = 999999


class Inventory:
    def __init__(self, catalog=None):
        if catalog is None:
            catalog = json.loads((Path(__file__).parent/'assets/items/catalog.json').read_text(encoding='utf-8'))
        self.catalog = deepcopy(catalog)
        self.definitions = self.catalog['items']
        self.grants = self.catalog.get('quest_grants', {})
        self.deliveries = self.catalog.get('deliveries', {})
        self._validate_catalog()
        self._items = {}
        self._granted = set()
        self._delivered = set()

    @staticmethod
    def _amount(value):return type(value) is int and 0 < value <= MAX_QUANTITY

    def _validate_catalog(self):
        if not isinstance(self.definitions, dict):raise ValueError('Items must be a mapping')
        for identifier, record in self.definitions.items():
            if (not isinstance(identifier, str) or not identifier or not isinstance(record, dict)
                    or record.get('category') not in CATEGORIES
                    or any(not isinstance(record.get(key), str) or not record[key] for key in ('name', 'description'))):
                raise ValueError('Invalid item definition')
        for bundle in self.grants.values():
            if not self._valid_bundle(bundle):raise ValueError('Invalid quest grant')
        for key, delivery in self.deliveries.items():
            if (not isinstance(delivery, dict) or not self._valid_bundle(delivery.get('items'))
                    or any(not isinstance(delivery.get(field), str) or not delivery[field]
                           for field in ('quest', 'objective', 'recipient'))
                    or key != delivery['quest']+'/'+delivery['objective']
                    or delivery['quest'] not in self.grants):
                raise ValueError('Invalid delivery')

    def _valid_bundle(self, bundle):
        return (isinstance(bundle, dict) and bool(bundle) and
                all(identifier in self.definitions and self._amount(quantity)
                    for identifier, quantity in bundle.items()))

    def quantity(self, identifier):return self._items.get(identifier, 0)

    def entries(self, category=None):
        if category is not None and category not in CATEGORIES:return []
        return [dict(deepcopy(self.definitions[identifier]), id=identifier, quantity=quantity)
                for identifier, quantity in sorted(self._items.items(),
                    key=lambda pair: (self.definitions[pair[0]]['name'].casefold(), pair[0]))
                if category is None or self.definitions[identifier]['category'] == category]

    def add_many(self, bundle):
        """Validate the entire bundle before adding anything."""
        if not self._valid_bundle(bundle):return False
        if any(self.quantity(key)+amount > MAX_QUANTITY for key, amount in bundle.items()):return False
        for key, amount in bundle.items():self._items[key] = self.quantity(key)+amount
        return True

    def add(self, identifier, quantity=1):
        return isinstance(identifier,str) and self.add_many({identifier: quantity})

    def _take(self, bundle):
        if not self._valid_bundle(bundle) or any(self.quantity(key) < amount for key, amount in bundle.items()):return False
        for key, amount in bundle.items():
            remaining = self.quantity(key)-amount
            if remaining:self._items[key] = remaining
            else:self._items.pop(key)
        return True

    def consume_bundle(self, bundle):
        """Consume a complete ordinary-item cost, leaving quest items protected.

        Validate every item and quantity before removing anything. Lattice
        activation can therefore charge several crystals as one transaction.
        """
        if not self._valid_bundle(bundle):return False
        if any(self.definitions[key]['category'] == 'key_items' for key in bundle):return False
        return self._take(bundle)

    def remove(self, identifier, quantity=1):
        """Ordinary use/sale/removal cannot consume protected quest items."""
        if not isinstance(identifier,str):return False
        if self.definitions.get(identifier, {}).get('category') == 'key_items':return False
        return self._take({identifier: quantity})

    def grant_quest(self, quest):
        if quest not in self.grants or quest in self._granted:return False
        if not self.add_many(self.grants[quest]):return False
        self._granted.add(quest)
        return True

    def was_granted(self, quest):return quest in self._granted

    def was_delivered(self, quest, objective):return quest+'/'+objective in self._delivered

    def deliver(self, quest, objective, recipient):
        """Consume a registered handoff once, without finishing its objective.

        The gameplay caller must also verify that the objective is active and
        the NPC interaction succeeded. Other tasks (e.g. sacks) remain separate.
        """
        key = quest+'/'+objective
        delivery = self.deliveries.get(key)
        if (delivery is None or key in self._delivered or quest not in self._granted
                or recipient != delivery['recipient']):return False
        if not self._take(delivery['items']):return False
        self._delivered.add(key)
        return True

    def to_dict(self):
        return {'version': 1, 'items': dict(sorted(self._items.items())),
                'granted_quests': sorted(self._granted), 'deliveries': sorted(self._delivered)}

    def restore(self, data):
        """Reject malformed snapshots atomically; never partially restore."""
        if (not isinstance(data, dict) or set(data) != {'version', 'items', 'granted_quests', 'deliveries'}
                or type(data['version']) is not int or data['version'] != 1):return False
        items, granted, delivered = data['items'], data['granted_quests'], data['deliveries']
        if (not isinstance(items, dict) or len(items) > len(self.definitions)
                or any(key not in self.definitions or not self._amount(value) for key, value in items.items())):return False
        for values, known in ((granted, self.grants), (delivered, self.deliveries)):
            if (not isinstance(values, list) or len(values) > len(known)
                    or any(not isinstance(value, str) or value not in known for value in values)
                    or len(values) != len(set(values))):return False
        if any(self.deliveries[key]['quest'] not in granted for key in delivered):return False
        self._items = dict(items)
        self._granted = set(granted)
        self._delivered = set(delivered)
        return True
