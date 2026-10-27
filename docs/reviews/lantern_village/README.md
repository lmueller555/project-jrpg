# What the Village Carries — review

The capture uses the production Game, normal walking, actual Venn and Elira cottage doors, companion staging and all eleven new dialogue callbacks. Only the already-shipped MQ04 PR1 frame checkpoint and earlier quests are seeded.

`quest.gif` contains every main dialogue page in a time-compressed overview. Use the native PNG stills and `dialogue.md` for readable scene review.

The endpoint is `elira_visited`: MQ04 remains active with its first four objectives complete. Liam’s frame and drawing remain at Mira’s workshop, Elira keeps her existing memorial lantern, and the mill remains running.

Reproduce with `python tools/capture_lantern_village.py`.

Validation: all **585 tests** pass, including **17 new village integration tests** and the **23 opening-segment tests**. The final actual-game capture reads 227 dialogue pages across all eleven new scenes and records eight companion transfers through both cottage doors. Mira returns to her original bench; Liam’s frame and drawing stay at her craft table, the Venn child remains resting, and Elira’s original lantern stays on its table.
