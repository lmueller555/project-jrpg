# Caelan's inventory

The satchel is available with **I** or **Pause → Inventory**. Its Weapons, Armor,
Items and Key Items tabs share the readable interface and text-size settings.
Mouse clicks or Tab/Left/Right select a category; Up/Down selects an item.
Wheel and Page Up/Down read longer contents; both columns have draggable scrollbars
when needed. I, Escape or the close button returns to gameplay, or to Pause when
opened there. Inventory freezes the world and preserves any conversation below it.

## Ownership and consumables

`assets/items/catalog.json` defines stable IDs, names, descriptions and categories.
`inventory.py` keeps positive integer quantities separately from definitions.
There is no weight or slot limit that could block a quest delivery. Identical
items are counted together, including spare weapons and armor. Distinct equipment
variants can have separate catalog IDs. Optional `equipment_slot` and `stats`
metadata is supported in the details pane. [Consumables](CONSUMABLES.md) now
support field and combat use. New journeys and quest playtests start with five
Potions, five Ethers, three Revival Salts, three Smoke Bombs and three Rest Kits.
Rest Kit use remains unavailable pending its resting rules. Crystal definitions
do not grant sample loot. Continue preserves actual saved quantities.

`add`, `add_many`, `quantity`, `entries`, `remove` and `consume_bundle` are the
ownership API. Bundles validate fully before mutation. `consume_bundle` rejects
unknown items, invalid quantities, insufficient stock and protected Key Items
before removing anything. Key Items cannot be removed through ordinary use,
selling or disposal. Registered quest handoffs use a separate API.

## Aether Crystals

Crystals appear in **Items** as materials reserved for future uses. Viewing a
crystal does not consume it or grant an attribute or ability. Ordinary New Game
starts without sample crystals.

| Item ID | Name |
| --- | --- |
| `aether_emerald` | Aether Emerald |
| `aether_sapphire` | Aether Sapphire |
| `aether_ruby` | Aether Ruby |
| `aether_amethyst` | Aether Amethyst |
| `aether_opal` | Aether Opal |
| `aether_topaz` | Aether Topaz |
| `aether_diamond` | Aether Diamond |

Battle item rewards use a receipt-backed operation. Replaying the same
completion does not duplicate its drops, including when inventory capacity
means no additional items can be received.

## Serene's request and delivery

`Game.accept_quest('CH01_MQ01')` grants Halden's medicine, Elira's food/oil bundle
and the Venn recovery supplies once, together with acceptance. Declining or
leaving the conversation grants nothing. The accepted click saves the supplies
in the same checkpoint as the follow-up scene. Opening inventory is optional;
the player does not have to manually select medicine to finish a handoff.

After the real NPC handoff succeeds, its controller calls:

```python
game.deliver_quest_item('CH01_MQ01', 'halden', 'halden')
```

This checks that the objective is active, the recipient matches the registered
delivery and all required quantities are held. Success removes the medicine,
records the delivery and checkpoints the journey. Repeating it has no effect.
Wrong recipients, queued objectives or missing items change nothing.

Medicine delivery does **not** complete Halden's objective: his three grain sacks
and Tomas's departure remain separate required tasks. The controller can query
`inventory.was_delivered(quest, objective)` to resume that visit after a reload.
Room entry never delivers an item. `halden_visit.py` now invokes this API at
Halden's actual handoff beat, then separately tracks the three sacks and Tomas's
goodbye. No debug delivery is exposed through the satchel UI. `elira_visit.py`
likewise consumes the food/oil bundle at the actual handoff beat, after Halden
unlocks the visit. The borrowed lantern is a visible quest prop with a saved
location (shelf, Caelan's hands, or table); it is not an extra supply bundle or
loot item.

## Saves

Journey saves include inventory quantities, granted-quest IDs and delivery
receipts, under an independently versioned inventory record. Invalid snapshots
are rejected before replacing live progress. Settings remain separate.

Older saves without inventory migrate quietly: accepted quests receive their
outstanding supplies; completed household objectives are treated as delivered.
Already recorded grants and receipts never replay or refill a delivered item.
New Game resets inventory and receipts, then supplies the fresh starting bundle. Completing a household through its quest
controller also retires any remaining supplies registered for that household.

## Eldenmere town services and gold

The Item Shop keeper offers **Buy / Leave** from the front of the counter.
The menu lists Potion, Ether, Revival Salts, Smoke Bomb and Rest Kit, showing
catalog descriptions, owned counts, unit price, quantity and total. All current
prices are **0 gold**. Rest Kits remain unavailable for use until their separate
resting policy is implemented; purchasing one does not enable it.

Use Up/Down (W/S) to select stock, Left/Right (A/D) to change quantity,
Page Up/Down to change by ten, and Enter/Space/E to open and accept confirmation.
Escape/Backspace cancels confirmation, then leaves the shop. Mouse controls
select stock, adjust quantity, buy, confirm/cancel and leave. The wheel scrolls
long descriptions. The shop freezes exploration and consumes conflicting menu
inputs; focus loss prevents purchases.

`assets/services/eldenmere.json` owns stock and prices. `economy.purchase` checks
stock membership, ordinary-item eligibility, strict positive integer quantity,
the existing shared inventory limit of 999999 per item, price and funds before
changing either inventory or gold. There is no shop-only capacity limit. Free
purchases use the same transaction path as future paid purchases. Selling,
equipment stock and currency rewards are not implemented here; exterior display
merchandise remains decoration.

Party currency is `game.wallet.gold`, shown in the shop and satchel. New journeys
start at zero; no starting-gold or monster-gold grants are introduced. Journey
snapshots store `gold` as a nonnegative integer up to 999999999. Older saves
without this optional field load with zero; invalid balances reject the entire
snapshot. New Game resets the wallet, while Continue and slot loading preserve it.

The Inn keeper offers **Stay — 0 gold / Leave**. Both the keeper and the guest bed
use the same service price and confirmed `BedRest` recovery/save path. Rest
restores HP and MP for every available party member, including reserves; it does
not reset quests, growth or add new status-cleansing rules. Cancellation or an
invalid approach changes nothing. A failed recovery checkpoint rolls back both
resources and any charge and offers Retry. The price remains zero in live data.

Successful purchases request one service autosave when their shop session closes;
confirmed inn stays request one after their recovery commits. Publication waits
for safe, focused exploration using the existing save guards. Browse/cancel-only
sessions do not request service saves. See [save behavior](SAVE_SYSTEM.md).
