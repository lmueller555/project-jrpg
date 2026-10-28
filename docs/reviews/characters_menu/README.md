# Characters menu, attribute icons and tooltips

Open **Pause → Characters** to inspect Caelan's attributes. His starting health
is **140/140 HP**, with 30/30 MP and nine other ratings of 10. Every attribute
has its own icon. Hover an icon or its card for the full explanation; arrows
or Tab expose the same information with keyboard focus. Closing Characters
returns to Pause and preserves any conversation underneath.

The menu captures below come from the production game using actual keyboard/menu
input and mouse-motion events. No combat, additional party members or quest
completion was invented for the preview. Reproduce the menu captures with:

```sh
python tools/capture_character_status.py
```

## All attributes

![Caelan's Characters menu with 140 HP and all eleven icons](characters_normal.png)

## Hover explanations

![Spirit's healing explanation](characters_hover_spr.png)

![Magick's damaging-spell explanation](characters_hover_mag.png)

![Health's maximum-resource explanation](characters_hover_hp.png)

## Enlarged text and screen edges

![Spirit's complete explanation at enlarged text size](characters_hover_spr_large.png)

![Luck's tooltip above the bottom row](characters_hover_lck_large.png)

![Complete MP tooltip at 480×320 with enlarged text](characters_hover_mp_small_large.png)

![Characters in the pause menu at enlarged text size](characters_pause_large.png)

## Attribute symbols

This contact sheet draws the same eleven symbols directly through the shared
icon renderer, in ordinary and selected colors at a 12-unit size.

![Eleven distinct attribute icons in ordinary and selected colors](icons.png)

## Saves and verification

New Game and journeys without an attribute record start at 140 HP. Older
version-one records with the original 300-HP baseline migrate to 140 while
preserving the health proportion, other attributes and MP. Incapacitated
characters remain at zero HP; a positive resource remains at least one HP.
Other saved growth and version-two records restore exactly. Continue commits
the migration once; reading the save at the title does not alter it.

Focused tests cover migration, icon bounds and distinctness, all eleven hover
tooltips at every supported text setting, keyboard parity, pointer/window
leave, letterboxed hit testing and modal conversation preservation. Tooltip
text remains complete and stays clear of the close button and footer.

The opening-route verifier also waits for temporary resident obstructions and
chooses a fresh approach when its target moves. Timing regressions cover these
cases, and permanently blocked routes still fail. Every main dialogue scene
remains required; this adjustment changes test navigation only.

See [capture metadata](verification.json) and the
[attribute reference](../../CHARACTER_ATTRIBUTES.md) for values and behavior.
