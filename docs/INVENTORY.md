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
effects belong to their future gameplay systems. The live catalog contains only
the opening quest's three real supply bundles, not starter equipment or sample loot.

`add`, `add_many`, `quantity`, `entries` and `remove` are the ownership API.
Bundles validate fully before mutation. Key Items cannot be removed through
ordinary use, selling or disposal. Registered quest handoffs use a separate API.

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
Room entry never delivers an item. Halden's actual actor, interaction and task
controller remain the next main-scenario milestone; no debug delivery is exposed
through the satchel UI.

## Saves

Journey saves include inventory quantities, granted-quest IDs and delivery
receipts, under an independently versioned inventory record. Invalid snapshots
are rejected before replacing live progress. Settings remain separate.

Older saves without inventory migrate quietly: accepted quests receive their
outstanding supplies; completed household objectives are treated as delivered.
Already recorded grants and receipts never replay or refill a delivered item.
New Game clears inventory and receipts. Completing a household through its quest
controller also retires any remaining supplies registered for that household.
