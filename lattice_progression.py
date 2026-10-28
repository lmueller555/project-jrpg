"""Atomic lattice operations across progression, inventory and live attributes."""
from copy import deepcopy

from aether_lattice import AetherLattice
from character_attributes import CharacterAttributes, MAX_ATTRIBUTE_VALUE


class LatticeProgression:
    """Validate complete commands before committing their related state.

    The caller checkpoints the whole journey after a successful operation.
    A failed disk write leaves the complete live operation pending for the
    normal save retry; it never persists a partial crystal purchase.
    """

    def __init__(self, lattice, inventory, attributes):
        self.lattice = lattice
        self.inventory = inventory
        self.attributes = dict(attributes)
        if any(identifier not in inventory.definitions
               or inventory.definitions[identifier]['category'] == 'key_items'
               for identifier in lattice.board.crystals):
            raise ValueError('Aether Crystals must be ordinary inventory items')

    def _commit(self, proposed_lattice, proposed_inventory, character_id=None, bonuses=None):
        prior_lattice = self.lattice.to_dict()
        prior_inventory = self.inventory.to_dict()
        if not self.lattice.restore(proposed_lattice.to_dict()):return False
        if not self.inventory.restore(proposed_inventory.to_dict()):
            self.lattice.restore(prior_lattice)
            return False
        if character_id is not None and not self.attributes[character_id].set_modifiers('lattice', bonuses):
            self.lattice.restore(prior_lattice)
            self.inventory.restore(prior_inventory)
            return False
        return True

    def move_reason(self, target, character_id='caelan'):
        if character_id not in self.attributes:return 'Unknown character.'
        return self.lattice.move_reason(target, character_id)

    def move(self, target, character_id='caelan'):
        if self.move_reason(target, character_id):return False
        return self.lattice.move(target, character_id)

    def activation_reason(self, target, character_id='caelan'):
        if character_id not in self.attributes:return 'Unknown character.'
        reason = self.lattice.activation_reason(target, character_id)
        if reason:return reason
        node = self.lattice.board.nodes[target]
        for identifier, quantity in node['cost'].items():
            if self.inventory.quantity(identifier) < quantity:
                name = self.inventory.definitions[identifier]['name']
                return f'Requires {quantity} {name} ({self.inventory.quantity(identifier)} owned).'
        if node['kind'] == 'stat':
            if self.attributes[character_id].value(node['stat'])+node['amount'] > MAX_ATTRIBUTE_VALUE:
                return 'This attribute cannot be increased further.'
        return ''

    def activate(self, target, character_id='caelan'):
        if self.activation_reason(target, character_id):return False
        # Copies validate all three effects before any shared live object changes.
        proposed_lattice = deepcopy(self.lattice)
        proposed_inventory = deepcopy(self.inventory)
        proposed_attributes = deepcopy(self.attributes[character_id])
        if not proposed_lattice.activate(target, character_id):return False
        bonuses = proposed_lattice.bonuses(character_id)
        if not proposed_attributes.set_modifiers('lattice', bonuses):return False
        if not proposed_inventory.consume_bundle(self.lattice.board.nodes[target]['cost']):return False
        return self._commit(proposed_lattice, proposed_inventory, character_id, bonuses)

    def award_battle_rewards(self, receipt_id, awards, drops):
        """Settle one completed battle attempt once, including all recipients.

        The future battle controller supplies a new receipt for every completed
        attempt, including genuine repeats of the same encounter.
        """
        if (not isinstance(awards, dict) or not isinstance(drops, dict)
                or not awards and not drops
                or any(identifier not in self.attributes for identifier in awards)
                or any(type(amount) is not int or amount <= 0 for amount in awards.values())
                or any(identifier not in self.lattice.board.crystals for identifier in drops)):
            return False
        proposed_lattice = deepcopy(self.lattice)
        proposed_inventory = deepcopy(self.inventory)
        if not proposed_lattice.award_rewards(receipt_id, awards):return False
        if drops and not proposed_inventory.add_many(drops):return False
        return self._commit(proposed_lattice, proposed_inventory)

    @classmethod
    def valid_journey(cls, data):
        """Validate canonical progression together without mutating title state."""
        if not isinstance(data, dict):return False
        lattice = AetherLattice()
        if 'aether_lattice' in data and not lattice.restore(data['aether_lattice']):return False
        record = data.get('character_attributes')
        if 'character_attributes' in data:
            if not isinstance(record, dict):return False
            if record.get('version') == 3 and 'aether_lattice' not in data:return False
            attributes = CharacterAttributes('caelan')
            if not attributes.restore(record, lattice_bonuses=lattice.bonuses('caelan')):return False
        elif any(lattice.state(identifier)['rp'] or lattice.state(identifier)['spent_steps']
                 or lattice.state(identifier)['activated'] for identifier in lattice.character_ids):
            return False
        return True
