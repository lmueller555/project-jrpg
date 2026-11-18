# First live standard-roster bindings

Seven explicitly selected actors now load their approved native idles, matching
eight-frame directional walks, and matching portrait references through
`npc_roster_art.py`. The source-of-truth selection is
`assets/characters/npc_roster_hd/live_bindings.json`.

| Existing actor | Design |
| --- | --- |
| Gardener's partner | adult_man_01 |
| Home B mother / father | adult_woman_01 / adult_man_02 |
| Home C mother / father | adult_woman_03 / adult_man_03 |
| Innkeeper | innkeeper_05 |
| Item shopkeeper | shopkeeper_03 |

## Scope and behavior

These seven are stationary home/service actors. They remain stationary: this
does not invent a daily schedule. Their four-direction idle and walk banks are
available on the same actor; external motion selects manifest timing rather than
assuming four legacy frames. Maps and builders still own IDs, positions, feet
blockers and initial placements. The registry overrides only visual selection
at runtime, so rebuilding any old source map cannot revert these seven actors.
No source maps, collision, quests, save schema, service logic, actor IDs or
approved asset images changed.

The current dialogue contains speakers for the two service keepers, but none
for the five generic household adults. Keepers now use unique roster portrait
keys rather than overwriting the shared male_01 portrait still used by the
driver/mason. Household actors retain matching portrait paths on their visual
bank for future authored dialogue; this pass does not invent dialogue or speakers.

The sanctuary gardener, named children/families, playable characters and
scripted special poses remain separate migrations.

## Verification

- 4 targeted roster tests verify all seven identities, original map records,
  positions/blockers/anchors, all 32 frames per actor, exact native output
  bytes, 70ms cadence and 560ms loops, portrait isolation and unmigrated child.
- 19 town service tests, 5 villager household tests, 15 social tests and
  12 settlement-household tests passed (55 total).
- Actual game captures at 960×640: [west cottage](home_a.png),
  [village cottage](home_b.png), [south cottage](home_c.png),
  [inn](inn.png), [shop](item_shop.png),
  [inn dialogue](inn_portrait.png), [shop dialogue](item_shop_portrait.png).
  Inspected actor feet, relative scale, counter occlusion and matching portraits.
- `observations.json` records live actor identity, binding, position and blocker.
- No change to fixed schedules and no new behavior/action animation is claimed.

Reproduce with `python tools/capture_npc_roster_bindings.py /tmp/npc-binding-review`;
the capture uses disposable saves and settings.
