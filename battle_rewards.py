"""Durable, item-only victory receipts independent of character progression."""
from copy import deepcopy
import re

from inventory import Inventory


MAX_RECEIPTS = 4096
_IDENTIFIER = re.compile(r'^[a-zA-Z0-9_.:/-]{1,128}$')
_FOCUS_REWARDS = {'boss:embravyr': 'red_focus_gem', 'boss:nivareth': 'white_focus_gem'}


def _identifier(value):
    return isinstance(value, str) and _IDENTIFIER.fullmatch(value) is not None


class BattleRewards:
    """Commit each completed encounter's inventory bundle at most once.

    This owner grants no XP or character stats. The caller checkpoints the
    receipt with the rest of the completed battle; failed saves retry that
    checkpoint without granting items again. Empty capped bundles still earn
    a receipt so a restored victory cannot manufacture another grant.
    """

    def __init__(self, inventory):
        if not isinstance(inventory, Inventory):
            raise ValueError('Battle rewards require an inventory owner')
        self.inventory = inventory
        self._receipts = set()

    def has_receipt(self, receipt_id):
        return isinstance(receipt_id, str) and receipt_id in self._receipts

    def award_battle_rewards(self, receipt_id, drops):
        if not _identifier(receipt_id):return False
        focus = _FOCUS_REWARDS.get(receipt_id)
        if focus is not None:
            from bestiary import load_bestiary
            enemy = receipt_id.split(':', 1)[1]
            limits = {row['item']: row['quantity'] for row in
                      load_bestiary()['enemies'][enemy]['rewards'].get('drop_table', [])}
            if (not isinstance(drops, dict) or type(drops.get(focus)) is not int
                    or drops.get(focus) != 1 or any(key != focus and
                       (key not in limits or type(amount) is not int or not 1 <= amount <= limits[key])
                       for key, amount in drops.items())):return False
        if (not _identifier(receipt_id) or self.has_receipt(receipt_id)
                or len(self._receipts) >= MAX_RECEIPTS
                or not isinstance(drops, dict)
                or any(not isinstance(identifier, str)
                       or identifier not in self.inventory.definitions
                       or self.inventory.definitions[identifier]['category'] == 'key_items'
                          and identifier != focus
                       or not Inventory._amount(amount)
                       for identifier, amount in drops.items())):
            return False
        proposed = deepcopy(self.inventory)
        if drops and not proposed.add_many(drops):return False
        if not self.inventory.restore(proposed.to_dict()):return False
        self._receipts.add(receipt_id)
        return True

    def to_dict(self):
        return {'version': 1, 'receipts': sorted(self._receipts)}

    def restore(self, data):
        if (not isinstance(data, dict) or set(data) != {'version', 'receipts'}
                or type(data['version']) is not int or data['version'] != 1
                or not isinstance(data['receipts'], list)
                or len(data['receipts']) > MAX_RECEIPTS
                or any(not _identifier(value) for value in data['receipts'])
                or len(set(data['receipts'])) != len(data['receipts'])):
            return False
        self._receipts = set(data['receipts'])
        return True

    @classmethod
    def valid_journey(cls, data):
        if not isinstance(data, dict):return False
        if 'battle_rewards' not in data:return True
        return cls(Inventory()).restore(data['battle_rewards'])
