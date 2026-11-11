# Consumables and cave supply drops

Item definitions and the fresh-run bundle live in
[`assets/items/catalog.json`](../assets/items/catalog.json). Ownership continues
to use the existing shared inventory and save format. The Items tab shows
quantities, descriptions and a Use button; Enter also begins field use.

| Item | Fresh-run quantity | Effect | Use |
| --- | ---: | --- | --- |
| Potion | 5 | Restore 100 HP, capped at maximum | One living available character; field or combat |
| Ether | 5 | Restore 15 MP, capped at maximum | One living available character; field or combat |
| Revival Salts | 3 | Revive a KO character with 25% maximum HP, rounded up | Field or combat |
| Smoke Bomb | 3 | Guaranteed escape when that encounter permits fleeing | Combat |
| Rest Kit | 3 | Resting policy not established yet | Collectible; use unavailable |

Starting supplies are created only with a fresh inventory for a new journey or
quest playtest. Accepting quests, revisiting a location, and Continue never
replenish them. Existing saves retain their actual quantities, including older
journeys with no consumables. Restarting a playtest creates a fresh bundle.
Gallery previews do not receive this bundle. Ordinary stack storage retains
the inventory's existing limit of 999,999 per item.

## Field and combat use

The field target picker includes available party members, including reserves
and KO characters. Potions/Ethers cannot revive; Revival Salts cannot target a
living character. Full HP/MP targets, unavailable characters and cancelled
selections consume nothing. Revival restores no MP. Smoke Bombs are combat-only;
Rest Kits cannot be used or consumed through either menu.

Field use saves the inventory cost and party resources together. A failed save
restores both and keeps the item. Use the keyboard or mouse to select a recipient;
Escape/Back cancels the recipient picker before closing the satchel.

Combat's **Items** command opens the shared supplies, then a recipient list.
Clicking a party status row can also select that recipient. Each use spends one
full ATB turn and zero MP. Recovery resolves at the item's impact, with colored
effects and positive recovery numbers. Revived characters return with zero ATB.
Guided tutorial commands retain control until their required lesson action has finished. Smoke Bombs obey
the same flee restrictions as the ordinary Flee command.

Supplies are local to the current combat attempt until settlement. Victory and
withdrawal commit used items together with the encounter's resources and rewards.
Defeat follows the existing encounter recovery policy and restores attempt
supplies. Continue during an unfinished fight restarts its checkpoint with its
entry supplies and resources. This matches the game's existing battle checkpoint
system rather than saving partially played actions.

## Bestiary drop tables

Each of Cave Bat, Lithrusk, Veylume, Embravyr, Nivareth and Vespermaw now has
the following `rewards.drop_table` in the [Bestiary](BESTIARY.md):

| Item | Independent chance per defeated enemy | Quantity on success |
| --- | ---: | ---: |
| Potion | 15% | 1 |
| Revival Salts | 10% | 1 |
| Ether | 5% | 1 |
| Rest Kit | 5% | 1 |

An enemy can drop none, one or several of these supplies. A group rolls once for
each enemy, rather than once for the whole encounter. The chance of at least one
supply from one enemy is approximately 30.96%; the average is 0.35 supplies per
enemy. Smoke Bombs have no random cave drop. MQ02's Boar and the optional town
Bat retain their existing guaranteed material rewards without these cave rolls.

Tables supplement guaranteed `rewards.drops`. Boss materials and the two
protected focus gems remain guaranteed and separate from random supplies.
Nothing is rolled or granted merely by previewing the Bestiary or preparing a
skipped-quest playtest checkpoint. No loot is awarded on fleeing or defeat.

Loot is shared party inventory, unlike EXP's full grant per surviving active
character. Spoils automatically collects the bundle once. Existing inventory
limits cap ordinary loot; using an item during combat opens space for that item's
drop. Focus gems remain protected, guaranteed and unique.

## Persistence and authoring

`enemy_loot.py` gives loot its own deterministic random stream from the saved
encounter identity and combat seed. Loot never consumes combat damage/ATB random
draws. Version-three and later Spoils store the rolled offer, received capped bundle,
used-item costs and the corresponding entry quantities. Continue and failed-save
retries reproduce the same offer and never repeat consumption or grants. Version-four victories additionally retain rig allocation and skill-healing facts,
as described in [Mira rig combat](MIRA_RIG_COMBAT.md). Earlier
version-one/two Spoils retain their original guaranteed-only rewards.

`consumables.py` shares restorative calculations between the model and field
controller. Catalogue `effect` records describe HP restoration, MP restoration,
percentage revival or escape. Invalid effect parameters, quantities, drop
chances, duplicate rows and probabilistic key-item drops are rejected. New item
variants can use the same effects without an item-specific implementation.

Later changes to drop probabilities must account for pending version-three/four
victories, just as EXP changes preserve existing reward plans. Combat/field
resting locations, shops, prices, damage items and status remedies remain future
work.
