# Eldenmere town services

The Item Shop keeper now offers five existing consumables through a quantity and
purchase-confirmation menu. The Inn keeper and guest bed share confirmed party
HP/MP recovery. Every live service costs **0 gold**. The wallet starts at zero;
starting-gold and monster-gold grants remain future work. Gear sales and selling
are outside this change; Rest Kits retain their explicitly unavailable use policy.

These are actual 960×640 Game window captures from disposable saves/settings:

- [Shop](shop.png), [purchase confirmation](purchase_confirmation.png),
  [purchased inventory count](purchase_complete.png).
- [Shop at 1.5× text](shop_large_text.png),
  [Rest Kit description at 1.5× text](rest_kit_large_text.png).
- [Inn confirmation](inn_confirmation.png), [large-text inn](inn_large_text.png),
  [recovery](inn_recovered.png), [satchel gold display](satchel_gold.png).

Visual review checked descriptions, quantity/total, confirmation/cancel buttons,
keeper identity and the largest text setting. Existing keeper sprites and their
matching male_01 portrait are reused; no character artwork was changed.
`observations.json` records an actual two-Potion purchase, zero remaining gold,
full HP after rest, and both shop/inn autosave reasons.

**122 distinct checks passed:** `regressions.json` contains the 120-check
inventory/rest/save/town/door selection; `services.json` contains 19 final service
checks, including two additional mouse/capacity cases. Covered paths include
paid-price validation for future use, insufficient funds, invalid quantities,
shared stack capacity, canceled/failed transactions, save-failure rollback and
retry, legacy currency defaults, malformed-currency rejection, real keeper input,
modal movement/input, focus loss, large text, service autosave throttling and
reload with the menu closed. The existing save suites include isolated playtests.

Reproduce:

```sh
python tools/check_eldenmere_hd.py test_town_services test_inventory test_inventory_gameplay test_bed_rest test_save_system_gameplay test_save_game test_save_library test_eldenmere_hd_integration test_doors --report /tmp/services-checks.json
python tools/capture_town_services.py /tmp/town-services-review
python tools/build_eldenmere_hd.py --check
```

The shared gameplay/pricing/save contract is documented in
[the inventory guide](../../INVENTORY.md#eldenmere-town-services-and-gold) and
[save guide](../../SAVE_SYSTEM.md); this folder records review evidence.
