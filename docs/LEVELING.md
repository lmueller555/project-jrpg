# Character and enemy leveling

This is the approved traditional leveling design and its live combat integration.
[`leveling.py`](../leveling.py) supplies character growth, XP curves and a
standalone level record. [`enemy_growth.py`](../enemy_growth.py) supplies the
enemy baseline and enemy-design catalogue. Their data lives in
[`level_growth.json`](../assets/characters/level_growth.json) and
[`enemy_archetypes.json`](../assets/combat/enemy_archetypes.json).

Live victories award EXP, stat growth and item drops through one receipt-backed
transaction. [`character_progression.py`](../character_progression.py) keeps the
party's level records and constructs deterministic before/after growth plans;
the combat owner validates, applies and checkpoints those plans with resources
and loot. New journeys use the approved level-one profiles for all five
characters. The existing Bat and Tusker retain their authored combat stats.

Older progression-backed saves receive a one-way compatibility import on
Continue: earned effective attributes, learned abilities and battle receipts are
preserved. A valid journey without `character_levels` begins at level one with
zero EXP, retaining its saved attributes, current HP/MP and earned modifiers.
Retired scores and movement currency are discarded without conversion to EXP;
past battle receipts do not create retroactive EXP. Validation on the title
screen does not rewrite the player's file. Future level-ups add the approved
growth differences to the preserved saved baseline rather than replacing it.

The [Bestiary](BESTIARY.md) now stores individual monster and boss definitions.
Cave Bat is the first computed species, explicitly authored at levels 2–3 with
84/104 EXP rewards. Victories sum the resolved monsters' EXP before allocating
it. The fixed test Bat uses a level-one reward reference, **60 EXP**, and the
MQ02 Ridgeback Tusker uses a level-three reference, **104 EXP**; these reward
references do not rescale either encounter's combat stats. Merely previewing a
species or constructing a battle model still grants nothing.

## Experience and levels

Characters progress from level **1 to 100**. Let `L` be the character's current
level and `M` the defeated monster's level:

```text
XP required to advance from L = 2 × round_half_up(100 × L^0.8)
Normal monster XP at M        = 2 × round_half_up(30 × M^0.5)
Boss XP at M                  = 10 × normal monster XP at M
```

Rounding occurs **before doubling**. A level-1 character needs **200 XP** to
reach level 2; a level-1 normal monster grants **60 XP**, or **600 XP** for the
boss reference. Ten times normal XP is the authored boss starting point, not a
ten-times multiplier on every boss stat.

| Level | XP to next level | Normal monster XP | Boss reference XP |
| ---: | ---: | ---: | ---: |
| 1 | 200 | 60 | 600 |
| 10 | 1,262 | 190 | 1,900 |
| 25 | 2,626 | 300 | 3,000 |
| 50 | 4,574 | 424 | 4,240 |
| 75 | 6,326 | 520 | 5,200 |
| 99 | 7,898 | 596 | 5,960 |
| 100 | MAX | 600 | 6,000 |

This preserves the intended increase from roughly 3.3 same-level monsters per
level early on to roughly 13.2 near the cap. Enemy counts per encounter and
ability availability still determine actual pacing.

**Every character in the active combat party who is alive at battle end receives
the full encounter XP on victory.** Sum the defeated monsters' rewards before
allocation; there is no split among survivors. KO'd combatants and reserves
receive zero. Summoned bots do not receive separate EXP or level records.
For example, three monsters worth 60 XP each award 180 XP to every surviving
combatant. Recipient eligibility uses actual end-of-battle HP before any
encounter-specific first aid. Fleeing or defeat grants no EXP, including when
some enemies were defeated before the escape or withdrawal.

`combat_xp_allocations(amount, active_ids, current_hp)` implements this selection
as a pure allocation helper. IDs are canonical character IDs such as `caelan`.
The HP mapping may contain the full roster, but only the supplied one-to-three
combat-party IDs receive allocations. The result includes each active ID with
its full amount or zero when KO'd; the helper does not mutate XP or resources.
The live victory coordinator uses this selection when it prepares the saved
growth plan; the view does not choose recipients or mutate progression.

## Character growth

All values below are natural, unmodified attributes. HP and MP are maxima;
current resources belong to the existing character state. New journeys use
these level-one baselines. Continued journeys retain their existing baselines,
including earlier guest or placeholder ratings, and receive the same approved
growth deltas on subsequent level-ups.

| Attribute | Caelan L1 | Mira L1 | Lucan L1 | Rhea L1 | Edran L1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| HP | 140 | 150 | 170 | 100 | 160 |
| MP | 30 | 30 | 20 | 45 | 40 |
| Strength | 10 | 10 | 12 | 6 | 7 |
| Magick | 10 | 10 | 7 | 13 | 7 |
| Spirit | 10 | 10 | 8 | 10 | 13 |
| Defense | 10 | 10 | 12 | 7 | 12 |
| Magick Defense | 10 | 10 | 9 | 10 | 12 |
| Speed | 10 | 10 | 8 | 10 | 8 |
| Accuracy | 10 | 10 | 11 | 10 | 9 |
| Evasion | 10 | 10 | 8 | 10 | 7 |
| Luck | 10 | 10 | 9 | 10 | 10 |

| Attribute | Caelan L100 | Mira L100 | Lucan L100 | Rhea L100 | Edran L100 |
| --- | ---: | ---: | ---: | ---: | ---: |
| HP | 5,600 | 5,800 | 7,400 | 3,600 | 6,500 |
| MP | 400 | 400 | 240 | 600 | 500 |
| Strength | 280 | 230 | 300 | 90 | 120 |
| Magick | 280 | 230 | 140 | 300 | 120 |
| Spirit | 200 | 230 | 170 | 190 | 300 |
| Defense | 220 | 230 | 300 | 120 | 280 |
| Magick Defense | 220 | 230 | 230 | 180 | 300 |
| Speed | 115 | 100 | 89 | 108 | 94 |
| Accuracy | 230 | 220 | 240 | 200 | 190 |
| Evasion | 190 | 190 | 150 | 180 | 140 |
| Luck | 200 | 200 | 180 | 200 | 180 |

The profiles establish these roles:

- **Caelan:** strong physical and magical offense for elemental swordplay.
- **Mira:** an even foundation across the five core offense, healing and defense
  ratings; bots and augments provide specialization.
- **Lucan:** physical offense, HP and physical defense, with lower Speed.
- **Rhea:** offensive spellcasting, high casting capacity and fragile defenses.
- **Edran:** high Spirit and both defenses, with low direct offenses.

Growth is fixed and deterministic:

```text
progress = (level − 1) / 99
natural stat = start + round_half_up((target − start) × progress^p)

p = 1.2  for HP and MP
p = 1.15 for ordinary ratings
p = 1    for Speed
```

The final Speed targets include both approved increases to Speed gained through
leveling. Starting Speed stays fixed. Ordinary ratings finish at or below 300,
leaving room for equipment, spells, items and signature mechanics.

| Attribute | Effective player cap |
| --- | ---: |
| HP | 9,999 |
| MP | 999 |
| Speed | 255 |
| Strength, Magick, Spirit, Defense, Magick Defense, Accuracy, Evasion, Luck | 999 |

The cap applies after named modifiers. The 300 natural-rating guideline is not
an effective combat cap. Character stats do not implicitly unlock new skills,
gems, gears, weapons, bots or augments.

### Current resources on level-up

**Level-ups do not restore HP or MP.** Increasing maximum HP or MP leaves its
current value unchanged, including zero HP. A character at 47/140 HP and 7/30 MP
who gains 20 maximum HP and 5 maximum MP becomes 47/160 HP and 7/35 MP.

`CharacterAttributes.apply_growth(gains)` applies validated nonnegative base-stat
gains while preserving current resources and existing named modifiers. It returns
`False` without mutation for invalid data. EXP award plans expose `stat_gains`;
the live progression coordinator applies them through this method after checking
the complete participating before-state. The method itself does not award EXP,
grant skills or own battle receipts. Existing encounter-specific first aid is
separate from level growth and does not change who qualified for EXP.

### Spoils and menus

Spoils displays the battle's total EXP and each combatant's portrait, level,
individual reward and progress toward the next level. The full reward appears
for each eligible survivor; KO rows explain their zero award. Bars fill together,
carry overflow through level thresholds and show **MAX LEVEL** at level 100.
Confirm can finish the animation without dismissing the result on the same
press; reduced motion keeps the information without the extended fill.

Each character who levels up receives one acknowledged sheet, combining all
levels gained in that battle. Its light parchment panel shows all attributes
with **black old values → green arrows → green new values**, plus numeric gains.
HP/MP rows describe maximum-capacity changes, not healing. The short original
EXP-fill cue and level-up chime use Effects volume; the previously interrupted
world or story music continues underneath the results. Items remain visible
with quantities, inspection details and inventory-limit information.

The Party menu shows levels in active slots and the recruited roster. The
Characters menu can inspect recruited companions and shows level, EXP progress
and remaining EXP alongside the selected character's attributes. Unrecruited
profiles do not become visible or join the party merely because a level record
exists for them.

### Mira's future inheritance rules

Bots may inherit different fractions of Mira's stats or augment her own stats.
For example, 1.5× her natural level-100 Strength of 230 yields 345 bot Strength;
a defensive bot granting +50% Defense yields 345 Defense from a natural 230.
These examples describe future configuration rules, not active bot code changes.

The existing damage formula squares offense, so 1.5× Attack produces about
2.25× damage at equal potency and target defense. Bot potency and cadence need
to account for that relationship. Whether inheritance reads natural stats,
equipment-adjusted stats or temporary buffs still needs an explicit rule, with
an evaluation order that prevents a bot's owner bonuses from feeding back into
its own inherited bonuses.

## Enemy baseline

Non-HP enemy attributes use **125% of the unrounded average** of all five
approved character curves at the same level. This is a fixed design reference;
active formation, equipment, buffs and story availability do not change it.
Intermediate values remain unrounded until the resulting enemy stat is rounded.

HP has its own larger curve, reflecting late-game skills, equipment and a
possible future Stagger damage window:

```text
Enemy HP = round_half_up(180 + 49,820 × progress^1.8)
```

| Level | Baseline enemy HP |
| ---: | ---: |
| 1 | 180 |
| 10 | 845 |
| 25 | 4,067 |
| 50 | 14,228 |
| 75 | 29,684 |
| 90 | 41,310 |
| 100 | 50,000 |

| Attribute | Enemy L1 baseline | Enemy L100 baseline |
| --- | ---: | ---: |
| HP | 180 | 50,000 |
| MP | 41 | 535 |
| Strength | 11 | 255 |
| Magick | 12 | 268 |
| Spirit | 13 | 273 |
| Defense | 13 | 288 |
| Magick Defense | 13 | 290 |
| Speed | 12 | 127 |
| Accuracy | 13 | 270 |
| Evasion | 11 | 213 |
| Luck | 12 | 240 |

Archetype, species and elite/boss adjustments apply afterward. Enemy HP may
exceed the player HP cap and is bounded by the existing **999,999,999** structural
limit. Effective ordinary ratings remain capped at 999, Speed at 255 and MP at
999. The player natural-rating guideline does not limit specialized enemy
ratings to 300.

The new growth builder uses MP 999 as its effective ceiling. Existing authored
enemy catalogues retain their independent structural HP/MP validation bounds;
this foundation does not rewrite their resources or introduce a new journey
validation rule.

The [enemy archetype catalogue](ENEMY_ARCHETYPES.md) separates ten approved
numerical stat profiles from fighting styles and twenty enemy concepts. Named
profile generation combines the raw baseline with the profile and explicit
species/tier factors before rounding once and applying caps. The Bat and Tusker
retain their authored live values while individual levels, species adjustments
and encounter tuning are defined.

## Progression API and persistence

```python
from leveling import (CharacterLevel, character_stats, combat_xp_allocations,
                      monster_xp, xp_to_next_level)
from enemy_growth import baseline_enemy_stats, profile_enemy_stats

xp_to_next_level(1)             # 200
monster_xp(1)                   # 60
monster_xp(1, boss=True)         # 600
character_stats('rhea', 100)['mag']  # 300
baseline_enemy_stats(100)['hp']  # 50000
profile_enemy_stats('brute', 100)['hp']  # 75000

# Mira is KO'd and Rhea is a reserve; only Caelan receives this reward.
combat_xp_allocations(180, ('caelan', 'mira'),
                      {'caelan': 47, 'mira': 0, 'rhea': 100})
# {'caelan': 180, 'mira': 0}

caelan = CharacterLevel('caelan')
receipt = caelan.award_xp(200)
assert caelan.level == 2
snapshot = caelan.to_dict()
clone = CharacterLevel.from_dict(snapshot)
assert clone.to_dict() == snapshot
```

The level record supports multiple level-ups from one award, derived stat gains,
and a versioned standalone snapshot:

```python
{'version': 1, 'character_id': 'caelan', 'total_xp': 200}
```

`CharacterLevel` exposes `character_id`, `total_xp`, `level`, `stats`,
`xp_into_level` and `xp_remaining`. Awards return an immutable `XpAward` with
requested, accepted and discarded XP; old/new total XP and level; per-stat gains;
and `levels_gained`. Exports are fresh copies.

Its total XP stops at the threshold for
level 100; the receipt distinguishes accepted XP from discarded overflow. An
invalid award or snapshot does not partially mutate a record. `xp_to_next_level`
returns 0 at level 100.

`total_xp_for_level(level)` gives the cumulative threshold, and
`level_for_total_xp(total)` resolves thresholds without awarding anything.
`raw_character_stats(character_id, level)` exposes the unrounded reference used
by the enemy baseline. Invalid levels, unknown characters, malformed records and
boolean numeric inputs are rejected.

`CharacterLevel` remains usable independently of a game. In live journeys,
`CharacterProgression(party)` owns one record for every canonical character and
saves them under the top-level `character_levels` field:

```python
{'version': 1, 'characters': {
    'caelan': {'version': 1, 'character_id': 'caelan', 'total_xp': 200},
    # The other four canonical character records are present too.
}}
```

`preview(amount, active_ids, end_hp)` produces a detached plan without mutation.
`valid_plan(plan)` recomputes its allocation, thresholds and growth;
`matches_plan(plan, after=False)` checks the participating saved before-state;
and `apply(plan)` commits all validated EXP and base-stat changes together.
Current resources, modifiers and exposed party attribute identities retain
their existing ownership. `initialize_new_game()` installs the approved
level-one stats only for a new journey; `restore(None)` resets EXP records
without replacing continued-journey stats.

New pending victory records use version 2 and include the progression plan,
actual end HP, before/after base stats and offered loot. Validation checks them
against the encounter, saved levels, party attributes and receipt stage.
Awarding items, EXP and growth is one atomic in-memory transaction, checkpointed
with battle resources. A failed checkpoint retries the already-awarded state
without applying the grant again. Animation skips, result dismissal and Continue
cannot manufacture another grant. Existing version-one pending victories remain
supported with their original item-only rewards and no retroactive EXP.

Use the headless [growth preview tool](../tools/preview_leveling.py) to inspect
the canonical curves without creating a game or reading a journey:

```sh
python tools/preview_leveling.py --levels 1 25 50 75 100 --format csv
python tools/preview_leveling.py --all-levels --format json
python tools/preview_leveling.py --enemy-profiles --all-levels --format csv
```

## Decisions still pending

- Recruitment levels, story-absence catch-up and expected campaign levels.
- Individual enemy levels, species adjustments and elite/boss tuning.
- Damage, healing, accuracy/evasion, critical and ATB balance at the new ranges.
- Elemental affinity assignment, equipment customization and Stagger design.

Live combat EXP payout, saved levels and the no-recovery rule are active.
Signature progression remains separate from natural level growth.
