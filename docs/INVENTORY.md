# Caelan's inventory

The satchel is available with **I** or **Pause → Inventory**. Its Weapons, Armor,
Items and Key Items tabs share the readable interface and text-size settings.
Mouse clicks or Tab/Left/Right select a category; Up/Down selects an item.
Wheel and Page Up/Down read longer contents; both columns have draggable scrollbars
when needed. I, Escape or the close button returns to gameplay, or to Pause when
opened there. Inventory freezes the world and preserves any conversation below it.

## Ownership and future item types

`assets/items/catalog.json` defines stable IDs, names, descriptions and categories.
`inventory.py` keeps positive integer quantities separately from definitions.
There is no weight or slot limit that could block a quest delivery. Identical
items are counted together, including spare weapons and armor. Distinct equipment
variants can have separate catalog IDs. Optional `equipment_slot` and `stats`
metadata is supported in the details pane; equipping, combat and consumable
effects belong to their future gameplay systems. The live catalog defines the
opening quest's three supply bundles and seven Aether Crystals. Normal New Game
starts with an empty satchel; crystal definitions do not grant sample loot.

`add`, `add_many`, `quantity`, `entries`, `remove` and `consume_bundle` are the
ownership API. Bundles validate fully before mutation. `consume_bundle` rejects
unknown items, invalid quantities, insufficient stock and protected Key Items
before removing anything. Key Items cannot be removed through ordinary use,
selling or disposal. Registered quest handoffs use a separate API.

## Aether Crystals

Crystals appear in **Items** and activate nodes through
**Pause → Aether Lattice**. Viewing a crystal in the satchel does not consume it
or grant a stat bonus. A successful activation consumes the complete required
bundle and records the activated node with the character's progression.

| Item ID | Name | Nodes |
| --- | --- | --- |
| `aether_emerald` | Aether Emerald | HP |
| `aether_sapphire` | Aether Sapphire | MP |
| `aether_ruby` | Aether Ruby | Str and Def |
| `aether_amethyst` | Aether Amethyst | Mag and M. Def |
| `aether_opal` | Aether Opal | Spr |
| `aether_topaz` | Aether Topaz | Speed, Acc, Eva and Lck |
| `aether_diamond` | Aether Diamond | Spells and abilities |

The future battle-reward interface grants shared crystal drops and individual
RP awards in one receipt-backed operation. Replaying the same completion does
not duplicate its rewards. The isolated lattice preview supplies test rewards
only to its temporary journey; opening quests and ordinary New Game grants
remain unchanged. See [Aether Lattice](AETHER_LATTICE.md).

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
New Game clears inventory and receipts. Completing a household through its quest
controller also retires any remaining supplies registered for that household.
