"""Shared restorative effects and atomic field use, without battle/UI imports."""
from inventory import Inventory, MAX_QUANTITY

def target_reason(effect, hp, mp, maximum_hp, maximum_mp):
    kind = effect.get('kind')
    if kind == 'revive':return '' if hp == 0 else 'Choose a KO character.'
    if hp == 0:return 'Use Revival Salts on a KO character.'
    if kind == 'restore_hp':return '' if hp < maximum_hp else 'HP is already full.'
    if kind == 'restore_mp':return '' if mp < maximum_mp else 'MP is already full.'
    return 'This item cannot be used on a character.'


def restore(effect, hp, mp, maximum_hp, maximum_mp):
    kind = effect['kind']
    if kind == 'restore_hp':hp = min(maximum_hp, hp+effect['amount'])
    elif kind == 'restore_mp':mp = min(maximum_mp, mp+effect['amount'])
    elif kind == 'revive':hp = max(1, (maximum_hp*effect['percent']+99)//100)
    return hp, mp


def valid_costs(costs, before):
    definitions = Inventory().definitions
    return (isinstance(costs, dict) and isinstance(before, dict) and set(costs) == set(before)
            and all(key in definitions and definitions[key].get('effect')
                    and type(count) is int and 1 <= count <= MAX_QUANTITY
                    and type(before[key]) is int and count <= before[key] <= MAX_QUANTITY
                    for key, count in costs.items()))


def resource_allowances(costs):
    definitions = Inventory().definitions
    hp = mp = 0
    for key, count in costs.items():
        effect = definitions[key]['effect']
        if effect['kind'] == 'restore_hp':hp += count*effect['amount']
        elif effect['kind'] == 'restore_mp':mp += count*effect['amount']
        elif effect['kind'] == 'revive':hp += count*9999
    return hp, mp


def field_reason(game, item_id, character_id=None):
    if not isinstance(item_id, str):return 'Choose an item.'
    item = game.inventory.definitions.get(item_id, {})
    if item.get('use_context') == 'rest_policy_pending':return 'Rest Kit use is not available yet.'
    if not item.get('effect'):return 'This item cannot be used directly.'
    if item['effect']['kind'] == 'escape':return 'This item is used during combat.'
    if not game.inventory.quantity(item_id):return 'None remaining.'
    if (game.on_title or game.combat.active or game.social.locked
            or game.opening_cinematic.active or game.transfer_cooldown):return 'Cannot use an item right now.'
    if character_id is None:return ''
    if character_id not in game.party.available_ids:return 'That character is unavailable.'
    target = game.party.characters[character_id]
    return target_reason(item['effect'], target.current_hp, target.current_mp,
                         target.value('hp'), target.value('mp'))


def use_field_item(game, item_id, character_id):
    reason = field_reason(game, item_id, character_id)
    if reason:return False, reason
    item = game.inventory.definitions[item_id]
    before_inventory, before_party = game.inventory.to_dict(), game.party.to_dict()
    target = game.party.characters[character_id]
    hp, mp = restore(item['effect'], target.current_hp, target.current_mp,
                     target.value('hp'), target.value('mp'))
    if (not game.inventory.consume_bundle({item_id: 1}) or not target.set_current(hp=hp, mp=mp)
            or game.save_store.enabled and not game.save_progress()):
        game.inventory.restore(before_inventory);game.party.restore(before_party)
        return False, 'Progress could not be saved. The item was kept.'
    return True, item['name']+' used on '+target.name+'.'
