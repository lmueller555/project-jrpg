# Consumable interface review

These are production Game renders from a disposable, completed-Mill fixture.
Caelan begins injured with no MP. Travel/ATB setup is shortened; Mira is then
explicitly set KO to demonstrate Revival Salts. No enemy HP or battle outcome
is edited, and these images do not claim a complete played victory.

- [Field recipients at 100% text](field_recipient_100.png)
- [Field recipients at 150% text](field_recipient_150.png)
- [Combat Items menu at 100% text](battle_items_100.png)
- [Combat Items menu at 150% text](battle_items_150.png)
- [Combat recipients at 150% text](battle_recipient_150.png)
- [Potion recovery](potion_impact_150.png)
- [Revival Salts recovery](revival_impact_150.png)
- [Smoke Bomb effect](smoke_impact_150.png)
- [Fixture and resource evidence](evidence.json)

Reproduce with `python tools/capture_consumables.py` in a configured Pygame
environment. Captures write only this review folder; game/settings state uses
temporary paths. See [Consumables](../../CONSUMABLES.md) for item, drop and save
rules. Used supplies shown here remain local to the unfinished battle attempt;
the actual victory/withdrawal persistence paths have separate gameplay tests.
