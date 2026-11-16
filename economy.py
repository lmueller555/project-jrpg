"""Party currency and atomic merchant purchases; no automatic gold grants."""
MAX_GOLD = 999999999


def valid_gold(value):
    return type(value) is int and 0 <= value <= MAX_GOLD


class Wallet:
    def __init__(self, gold=0):
        if not valid_gold(gold):raise ValueError('Invalid gold balance')
        self.gold = gold

    def spend(self, amount):
        if not valid_gold(amount) or amount > self.gold:return False
        self.gold -= amount
        return True


def purchase(inventory, wallet, stock, identifier, quantity):
    """Validate the complete transaction before changing either resource."""
    from inventory import MAX_QUANTITY
    if (not isinstance(identifier, str) or identifier not in stock
            or type(quantity) is not int or not 1 <= quantity <= MAX_QUANTITY):
        return False, 'Choose a valid item and quantity.'
    record = inventory.definitions.get(identifier)
    price = stock[identifier]
    if not record or record['category'] != 'items' or not valid_gold(price):
        return False, 'This item is not for sale.'
    if inventory.quantity(identifier)+quantity > MAX_QUANTITY:
        return False, 'Your satchel cannot hold that many.'
    total = price*quantity
    if total > wallet.gold:return False, 'Not enough gold.'
    if not inventory.add(identifier, quantity):return False, 'The items could not be added.'
    wallet.gold -= total
    return True, f'Purchased {quantity} × {record["name"]} for {total} gold.'
