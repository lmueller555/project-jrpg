# Bestiary dictionary

[`assets/combat/bestiary.json`](../assets/combat/bestiary.json) is the canonical
dictionary for monster and boss definitions. Entries are keyed by stable enemy
IDs under `enemies`. [`bestiary.py`](../bestiary.py) validates the complete
dictionary and resolves a species at an explicitly selected level.

The dictionary contains four computed Sanctuary cave species: **Cave Bat**,
**Lithrusk**, **Veylume** and the level-seven miniboss **Vespermaw**. Vespermaw is
a one-time story encounter in the cave's final Echo Chamber, with its dedicated
sprite bank and full combat cycle. The dictionary preserves the existing fixed
Bat and Ridgeback Tusker records for
their authored test and MQ02 encounters. Fixed records
retain their exact stats, abilities and item drops. Their computed-species
tuning and elemental profiles have not been assigned. The live victory owner
uses a level-one reward reference for the test Bat (**42 EXP**) and level three
for the Ridgeback Tusker (**73 EXP**) without rescaling either fixed encounter.

This is an authoring dictionary and combat adapter. The three normal cave
species are used by the [Sanctuary random encounter system](CAVE_RANDOM_ENCOUNTERS.md).
The dictionary does not add a player-facing encyclopedia menu. Its resolved EXP
feeds the live victory progression flow described in [Leveling](LEVELING.md):
every living active combatant receives the full sum for the encounter, with
saved levels and stat growth. Resolving or previewing dictionary data alone
does not grant rewards.

## Cave Bat

| Property | Definition |
| --- | --- |
| ID | `cave_bat` |
| Habitat | Caves along the Elden Vale Sanctuary's eastern ridge |
| Level range | 2–3 |
| Tier | Normal enemy |
| Family | Flying beast |
| Elemental identity | Non-Elemental: an unaligned creature |
| Combat concept | Battlemage: mixed physical and magical offense |
| Stat profile | Hybrid |
| Fighting style | Physical/Magical Alternation |
| Species adjustments | HP ×0.40, MP ×0.10, Evasion ×1.20; all other factors ×1 |
| Targeting | Cycle through living party members, skipping KO members |

Stats are computed from the [shared enemy baseline and profile](ENEMY_ARCHETYPES.md),
with species and tier factors applied before the single final rounding/cap step.
The dictionary stores the growth parameters, not duplicated level-by-level
attribute tables.

| Attribute | Level 2 | Level 3 |
| --- | ---: | ---: |
| HP | 73 | 85 |
| MP | 5 | 5 |
| Strength | 13 | 15 |
| Magick | 14 | 15 |
| Spirit | 11 | 13 |
| Defense | 13 | 14 |
| Magick Defense | 13 | 14 |
| Speed | 13 | 14 |
| Accuracy | 14 | 15 |
| Evasion | 15 | 16 |
| Luck | 13 | 15 |
| XP reward | 59 | 73 |

| Ability | Action ID | Damage | Potency | MP |
| --- | --- | --- | ---: | ---: |
| Bite | `cave_bat_bite` | Physical | 0.60 | 0 |
| Wing Gust | `cave_bat_wing_gust` | Non-elemental magical | 0.65 | 2 |

The sequence is **Bite → Wing Gust → Bite → Wing Gust → Bite…**. Five MP permits
two Gusts; thereafter the free Bite remains available. Each action spends a
normal ATB turn. Namespaced action IDs preserve the original test Bat's stronger
action definitions. Existing Bat sprites and presentation aliases supply the
flight, Bite, Gust, hit and defeat art without changing gameplay action IDs.

Against unmodified Caelan at the same level and 100% damage variance, Bite/Gust
deal 18/22 damage at level 2 and 24/26 at level 3. Ordinary attacks defeat one in
roughly three to four hits. Encounter guidance recommends one Cave Bat for solo
Caelan and pairs after the combat party expands; this guidance does not place
or spawn encounters.

The Cave Bat’s elemental profile is authored below. Aqua Edge now reads its
Water response in battle. Its planned low Stagger resistance remains future
work. Item drops remain explicitly pending; the resolved combat bundle is
empty until loot is authored. No item or drop chance is invented by the loader.

## Lithrusk and Veylume

These two normal species complement the Cave Bat's mixed offense. Lithrusk is
a slow, sturdy physical attacker; Veylume delivers stronger magical attacks
from a fragile body. Both have dedicated combat sprite banks and working
action presentation, documented in [Cave enemy combat art](CAVE_ENEMY_COMBAT_ART.md).

| Property | Lithrusk | Veylume |
| --- | --- | --- |
| ID | `lithrusk` | `veylume` |
| Family | Cave crustacean | Aether-adapted insect |
| Habitat | Splitstone Hollow and lower damp passages | Crystal galleries and the deeper approach |
| Level range | 2–3 | 3–4 |
| Element | Ground | Electric |
| Combat concept | Bulwark | Arcanist |
| Stat profile | Armored | Caster |
| Fighting style | Standard Attacks | Magical Offense |
| Species adjustments | HP ×0.50, MP ×0 | HP ×0.40, MP ×0.15 |
| Planned Stagger resistance | High | Low |
| Encounter guidance | One specimen | One specimen |
| Drops | Pending | Pending |

All omitted species multipliers are ×1, with no additional tier multiplier.
Stats use the approved baseline/profile composition and one final rounding
step, just like Cave Bat. The stat tables below are resolved documentation;
the dictionary retains growth parameters rather than duplicated stat tables.

| Attribute | Lithrusk L2 | Lithrusk L3 | Veylume L3 | Veylume L4 |
| --- | ---: | ---: | ---: | ---: |
| HP | 120 | 140 | 67 | 82 |
| MP | 0 | 0 | 10 | 11 |
| Strength | 11 | 13 | 7 | 8 |
| Magick | 10 | 11 | 18 | 20 |
| Spirit | 13 | 14 | 16 | 17 |
| Defense | 23 | 25 | 10 | 11 |
| Magick Defense | 8 | 10 | 17 | 19 |
| Speed | 10 | 11 | 12 | 13 |
| Accuracy | 14 | 15 | 15 | 17 |
| Evasion | 12 | 14 | 14 | 15 |
| Luck | 13 | 15 | 15 | 16 |
| XP reward | 59 | 73 | 73 | 84 |

| Ability | Action ID | Category / element | Potency | MP |
| --- | --- | --- | ---: | ---: |
| Claw Clamp | `lithrusk_claw_clamp` | Physical / Non-Elemental | 0.65 | 0 |
| Shell Bash | `lithrusk_shell_bash` | Physical / Non-Elemental | 0.80 | 0 |
| Static Spark | `veylume_static_spark` | Magical / Electric | 0.60 | 0 |
| Gather Charge | `veylume_gather_charge` | Preparation | 0 | 0 |
| Veinflash | `veylume_veinflash` | Magical / Electric | 1.00 | 4 |

Lithrusk's authored sequence is **Claw Clamp → Shell Bash**, with Claw Clamp
as its free fallback. Both attacks remain available without MP. Its mineral
plates suggest physical durability, but basic attacks remain viable and
Aether Edge's magical component provides another useful response.

Veylume's intended sequence is **Static Spark → Gather Charge → Veinflash**.
Gather Charge spends a preparation turn and signals the larger discharge.
Both levels have enough MP for two Veinflashes, leaving two or three MP.
Static Spark is the free fallback. The action selector skips Gather Charge
whenever Veinflash is unaffordable, then relies on Static Spark. Preparation
locks a living target for Veinflash and retargets if that character is defeated.
The adapter supports this Magical Offense pattern independently of the
Tusker's charge behavior. A charged hover loop remains visible between turns.

Against unmodified same-level Caelan at 100% damage variance, Lithrusk's
Claw Clamp/Shell Bash deal 14/17 damage at level 2 and 19/24 at level 3.
Veylume's Static Spark/Veinflash deal 34/57 at level 3 and 42/70 at level 4.
Caelan's ordinary attacks defeat Lithrusk in roughly six to seven hits and
Veylume in three. These checks use unchanged damage formulas and neutral
elemental behavior; they do not activate affinities or retune player stats.

| Incoming element | Lithrusk | Veylume |
| --- | ---: | ---: |
| Non-Elemental | 100% damage | 100% damage |
| Fire | 100% damage | 100% damage |
| Electric | 50% damage | 100% healing (absorb) |
| Water | 150% damage | 100% damage |
| Ice | 100% damage | 100% damage |
| Nature | 100% damage | 100% damage |
| Wind | 100% damage | 100% damage |
| Holy | 100% damage | 100% damage |
| Ground | 100% healing (absorb) | 200% damage |

Lithrusk's pale limestone plates and heavy gait suggest Ground alignment;
water wears its porous shell and dry mineral plates insulate it against
Electric attacks. Veylume's sparking antennae and luminous wing veins reveal
Electric alignment; Ground disperses its stored charge. Its light belongs to
a living insect adapted to ambient Aether. These profiles remain hidden
authoring data until elemental combat and deliberate reveal mechanics exist.

## Vespermaw

Vespermaw is a living cave predator adapted to the Sanctuary's Aether confluence.
Its pale body carries mineral crusts along the shoulders and spine, threaded
with violet and blue microcrystals. Recent disturbances have agitated it and
driven it out of the deeper passages. It is not undead, and its Holy affinity
is neutral.

| Property | Definition |
| --- | --- |
| ID | `vespermaw` |
| Family | Aether-adapted beast |
| Habitat | Elden Vale Sanctuary cave, final Echo Chamber |
| Level range | 7–7; an explicit level of 7 is required |
| Tier | Boss |
| Element | Ground |
| Combat concept | Windup Attacker |
| Stat profile | Brute |
| Fighting style | Telegraphed Windup |
| Species adjustments | Magick ×1.35, Speed ×0.80 |
| Tier adjustments | HP ×2.50 |
| Encounter | One-time Echo Chamber story battle with one Vespermaw |
| Planned Stagger resistance | Normal (moderate) |

All omitted multipliers are ×1. The approved profile, species and tier factors
are composed before the single final rounding/cap step.

| Attribute | Level 7 |
| --- | ---: |
| HP | 1,877 |
| MP | 29 |
| Strength | 24 |
| Magick | 18 |
| Spirit | 17 |
| Defense | 26 |
| Magick Defense | 18 |
| Speed | 11 |
| Accuracy | 23 |
| Evasion | 19 |
| Luck | 21 |
| XP reward | 1,110 |

The reward is ten times the reduced level-seven normal-monster reward of
111 EXP. On victory, each surviving active combatant receives
the full 1,110 EXP. Guaranteed drops are one `aether_amethyst` and one
`aether_sapphire`, both existing material items. Previewing this record does
not grant EXP, items or story progress.

The approved action design is retained in the entry's validated `combat_design`
block with `status: ready`, and its five actions are registered in the live
action catalogue:

| Ability | Action ID | Category / target | Potency | MP |
| --- | --- | --- | ---: | ---: |
| Raking Claw | `vespermaw_raking_claw` | Non-Elemental physical / one character | 0.65 | 0 |
| Confluence Roar | `vespermaw_confluence_roar` | Non-Elemental magical / all living party members | 0.50 each | 6 |
| Gather Resonance | `vespermaw_gather_resonance` | Preparation / self | 0 | 0 |
| Ruinous Pounce | `vespermaw_ruinous_pounce` | Non-Elemental physical / marked character | 1.40 | 0 |
| Exhausted | `vespermaw_exhausted` | Recovery / self | 0 | 0 |

The live cycle is **Raking Claw → Confluence Roar → Gather Resonance →
Ruinous Pounce → Exhausted**, then repeat. Raking Claw is the free fallback
when the Roar's MP cost cannot be paid. Single-target pressure cycles through
living party members. Gather Resonance announces and locks the Pounce target;
that character must receive at least one opportunity to act before the hit.
Retargeting requires a fresh warning and another response opportunity.
Confluence Roar resolves a separate magical hit against each living active
party member. Each member's Magick Defense, Guard and variance apply to their
own hit; KO characters and bots are excluded. Its six MP is spent once.

After Pounce, Vespermaw takes 25% more damage and spends its next turn recovering.
That vulnerability ends immediately before the next Raking Claw begins. This
window is independent of the future Stagger mechanic. Initial tuning assumes
a rested three-character party around levels five through seven and does not
require in-battle healing. The current pending-MQ03 route naturally provides
Caelan and Mira; a rested level-six-to-seven pair has enough damage and
survivability when using Aether Edge, Overclock and Guard against the marked
Pounce. This encounter does not recruit Lucan or change his story ownership.

| Incoming element | Response |
| --- | ---: |
| Non-Elemental | 100% damage |
| Fire | 100% damage |
| Electric | 50% damage |
| Water | 150% damage |
| Ice | 100% damage |
| Nature | 100% damage |
| Wind | 100% damage |
| Holy | 100% damage |
| Ground | 100% healing (absorb) |

The mineral crust and heavy gait suggest Ground alignment. The crust insulates
against Electric attacks but is vulnerable to erosion by Water. Ground
absorption takes precedence over its stored damage percentage. As with the
other species, elemental responses and Stagger remain hidden planning data.

`combat_design.status` is `ready` and `metadata['combat_pending']` is false.
Party-wide damage, the recovery vulnerability and the guaranteed marked-character
response opportunity are active. Pending designs for future enemies remain
blocked by the adapter until their own action rules are implemented.
Presentation references the dedicated `vespermaw` bank, with direct aliases
from the five designed action IDs to their matching animation states. The
[combat art bank](VESPERMAW_COMBAT_ART.md) supplies 256 authored poses across
ten animations, including idle, prowl, charged hold, hurt and defeat.

Approaching the Echo Chamber offers **Enter / Party / Step back**. Entry uses a
short crystal-and-growl introduction and the dedicated Echo Chamber battlefield.
Party selection respects existing story locks and never heals or levels anyone.
The fight uses the ordinary 0–50% opening ATB range; its saved combat seed makes
an unfinished entry repeatable on Continue. Flee is unavailable during this boss
battle. Defeat offers **Retry / Return to the Quiet Shelf**, restoring captured
entry HP/MP and granting no rewards. Recovery remains available at the nearby
Sanctuary visitor bed after leaving the cave.

The boss has its own durable state and fixed reward receipt. The defeated flag
is saved with the XP/drop transaction, and pending spoils remain resumable after
a failed save or Continue. A completed victory permanently disables the trigger;
revisiting cannot repeat rewards. It remains excluded from random pools and does
not complete MQ03, resolve the pending Sanctuary arrival, change escort ownership
or end Kindled Courage. See the [live encounter review](reviews/vespermaw_encounter/README.md).

## Authoring before art

An unfinished species uses `"presentation": {"sprite_id": null,
"action_aliases": {}}`. The loader validates and resolves its complete data
without requiring art files. `metadata['presentation_pending']` reports this
state; the overview and stat previews also include a `presentation_pending`
column. Concrete sprite IDs require an existing animation manifest and
authored states for every action. Lithrusk and Veylume now resolve to their own
ready sprite banks with empty alias maps; their action records name the poses
directly.
Pending combat designs may alias their local action IDs directly to manifest
states; those aliases are checked against the actual bank. Live action aliases
retain their existing catalog validation.
Pending art requires empty aliases and cannot silently borrow another enemy's
appearance. `BattleModel.from_bestiary` rejects it before constructing a battle.

Physical and magical actions can carry an optional canonical `element` tag,
separately from their damage category and the species' defensive affinities.
Utility actions remain untagged. Aqua Edge tags only its magical Spellblade
component as Water and reads the target’s authored percentage or absorption.
Existing enemy attack tags continue to preserve design intent; their visual
Electric projectiles do not by themselves grant player elemental profiles.
Cave encounter pools and multi-enemy battle
selection are documented in [Random encounters](CAVE_RANDOM_ENCOUNTERS.md).

## Elemental identity and relationships

The canonical roster is **Non-Elemental, Fire, Electric, Water, Ice, Nature,
Wind, Holy and Ground**. Nature replaces the proposed Poison element and keeps
Caelan’s planned Nature focus within the roster; the opening gift installs
only Blue Water. Poison status, if introduced, is separate from an elemental
damage type.

Every computed species includes an `elemental_profile` with:

- `element`: one canonical elemental ID.
- `damage_percentages`: an explicit percentage for all nine types, from 0
  through 200 inclusive. Intermediate values such as 75 or 125 are valid.
  Zero means immunity, 100 means neutral damage and 200 means double damage.
- `absorption`: the matching elemental ID in `elements`, and
  `healing_percent: 100`. An elemental creature absorbs its own type;
  `non_elemental` means no alignment and requires an empty absorption list.
- `design_rationale`: authoring notes explaining the creature's identity and
  the clues supporting its weaknesses, resistances and immunities.

Absorption overrides the damage percentage for that type. It restores 100% of
the hit's damage at neutral affinity, with applicable damage modifiers and the
normal damage cap, up to the target's missing HP. A miss restores nothing, and
absorption cannot revive a defeated enemy. The complete percentage table is
still required; it must not disguise absorption as a negative percentage.

Elemental identity is independent of the elements a creature can attack with,
and physical/magical damage categories remain independent of element. Flying
does not automatically make a creature Wind-aligned; living creatures are not
automatically Nature-aligned. No universal weakness wheel overrides the
species' authored relationships.

For Cave Bat, both levels use this profile:

| Incoming type | Damage received | Absorption |
| --- | ---: | --- |
| Non-Elemental (`non_elemental`) | 100% | None |
| Fire (`fire`) | 200% | None |
| Electric (`electric`) | 100% | None |
| Water (`water`) | 100% | None |
| Ice (`ice`) | 100% | None |
| Nature (`nature`) | 100% | None |
| Wind (`wind`) | 100% | None |
| Holy (`holy`) | 100% | None |
| Ground (`ground`) | 100% | None |

Its natural fur, fragile leathery wings and lack of an elemental aura support
an unaligned identity. Fire threatens its thin wing membranes. Its flight and
cave habitat do not imply Wind or Ground alignment, and dark surroundings do
not make it undead or Holy-weak. Wing Gust remains non-elemental magical damage.

The corresponding species block is:

```json
"elemental_profile": {
  "element": "non_elemental",
  "damage_percentages": {
    "non_elemental": 100,
    "fire": 200,
    "electric": 100,
    "water": 100,
    "ice": 100,
    "nature": 100,
    "wind": 100,
    "holy": 100,
    "ground": 100
  },
  "absorption": {"elements": [], "healing_percent": 100},
  "design_rationale": "An unaligned cave creature with fragile wings vulnerable to fire."
}
```

These are internal design data, hidden during ordinary play. A monster's name,
appearance, environment and behavior should support an informed guess about
its element and affinities. Use consistent clues across related creatures;
surprising exceptions need their own recognizable clue. Edran's planned
**Study** ability will be one of the limited ways to reveal enemy data directly.
Aqua Edge applies these data to its magical component. This does not implement
Study or add automatic HUD affinity labels.

The old partial `planned_mechanics.elemental_affinities` map has been replaced
by this complete profile. `planned_mechanics` now contains only Stagger design.
Fixed prototype encounters have unassigned elemental data; the loader does not
invent affinities for them.

## Dictionary and resolution API

```python
from bestiary import build_enemy, load_bestiary

catalogue = load_bestiary()
assert 'cave_bat' in catalogue['enemies']

bat = build_enemy('cave_bat', 2)
assert bat['combat']['name'] == 'Cave Bat'
assert bat['combat']['attributes']['hp'] == 73
assert bat['xp_reward'] == 59
assert bat['metadata']['drops_pending']
assert bat['metadata']['elemental_profile']['element'] == 'non_elemental'
assert bat['metadata']['elemental_profile']['damage_percentages']['fire'] == 200

lithrusk = build_enemy('lithrusk', 2)
assert lithrusk['combat']['attributes']['hp'] == 120
assert not lithrusk['metadata']['presentation_pending']
assert lithrusk['presentation']['sprite_id'] == 'lithrusk'

fixed = build_enemy('bat')
assert fixed['combat']['attributes']['hp'] == 72
assert fixed['level'] is None
assert fixed['xp_reward'] is None
```

Fixed records intentionally retain their unassigned species level and EXP in
this adapter. [`post_battle.battle_reward_definition`](../post_battle.py) supplies
the explicit test-Bat/MQ02 reward references when settling a live victory; it
does not turn the fixed records into computed species or alter their attacks.

`load_bestiary(data=None, actions=None)` returns a validated, detached dictionary.
An optional `actions` argument supplies an already validated action dictionary.
`build_enemy(enemy_id, level=None, *, data=None, actions=None)` returns a fresh
resolved record containing `id`, `level`, `xp_reward`, `combat`,
`fighting_style`, `behavior`, `presentation` and `metadata`.

The `combat` block contains exactly `name`, `attributes`, `abilities` and
`rewards`. Supported live species are compatible with the existing battle
validator; pending `combat_design` entries preserve their local action IDs and
are rejected by the adapter before battle construction. Elemental design is
retained in `metadata['elemental_profile']` and read by Aqua Edge’s Water
magical component.
Behavior, presentation and future-mechanic information retain separate ownership.
Species require an explicit level within their authored range; fixed records
accept no level.
Unknown IDs, malformed ranges, invalid references, non-finite multipliers and
missing free fallback actions are rejected.

```python
from battle_model import BattleModel
from character_attributes import CharacterAttributes

model = BattleModel.from_bestiary(CharacterAttributes(), 'cave_bat', 2)
assert model.enemy.name == 'Cave Bat'
assert model.enemy_level == 2
assert model.enemy_xp_reward == 59
assert model.enemy_sprite_id == 'bat'
```

`BattleModel.from_bestiary(player_attributes, enemy_id, level, *,
bestiary_data=None, **options)` exposes the resolved metadata through
`enemy_bestiary_id`, `enemy_level`, `enemy_xp_reward`, `enemy_sprite_id` and
`enemy_action_aliases`, plus the detached `enemy_bestiary_record`. Constructing
the model does not award EXP or serialize a new world encounter. The victory
coordinator sums these resolved rewards, applies survivor eligibility before
post-battle first aid and settles EXP with item drops and stat growth exactly
once. KO combatants, reserves and bots receive no EXP; fleeing or defeat grants
none. Unsupported future fighting styles remain data until their action
selection and behavior are implemented; the combat adapter rejects them rather
than silently substituting another style.

## Adding another monster or boss

1. Copy the computed Cave Bat entry under a new stable ID. Retain
   `"mode": "species"` and author its name, description, family, habitats and
   inclusive `level_range` (`min` and `max`).
2. Select an approved stat profile and combat concept, then supply explicit
   `species_multipliers` and `tier_multipliers`. Omitted attribute factors are
   ×1. Keep the common growth curve in the growth backend.
3. Register any supported new action definitions in
   [`actions.json`](../assets/combat/actions.json), then reference their IDs in
   the sequence and free fallback. Choose a supported targeting policy and
   fighting style, or implement the missing behavior before battle use.
   An authoring-only `combat_design` can retain unsupported actions and their
   windup/recovery rules with `status: pending_runtime`; these records remain
   unavailable to the combat adapter until runtime support is implemented.
   A `ready` design must match its registered live actions and supported rules.
4. Author a complete `elemental_profile`, including all nine damage percentages,
   matching-element absorption and a rationale for the clues players can infer.
   Consider identity early enough to inform the monster's name, visual design,
   habitat and behavior. Keep the data hidden except through deliberate reveal
   mechanics such as the planned Study ability.
5. Author presentation references, or use an explicit null sprite ID with empty
   action aliases while art is pending. Mark future mechanics and undecided
   drops. Reusing art is independent of gameplay action identity.
6. Preview every level in the range and test the resolved combat behavior.

Use `"tier": "normal"` for an ordinary monster. For a boss, use
`"tier": "boss"` and author its durability/offense adjustments in
`tier_multipliers`.
XP derives from the normal level curve with the established ten-times boss
factor. Boss status does not imply ten-times HP or ten-times every stat.

The legacy four-field authored records remain supported for compatibility.
New ordinary monsters and bosses should use computed species definitions so
their stats remain consistent with approved growth and profile data.

## Headless preview

```sh
python tools/preview_bestiary.py --list
python tools/preview_bestiary.py --enemy cave_bat --levels 2 3
python tools/preview_bestiary.py --enemy cave_bat --levels 2 3 --format json
python tools/preview_bestiary.py --enemy cave_bat --levels 2 3 --format csv
python tools/preview_bestiary.py --enemy lithrusk --levels 2 3
python tools/preview_bestiary.py --enemy veylume --levels 3 4
python tools/preview_bestiary.py --enemy vespermaw --levels 7
python tools/preview_bestiary.py --enemy vespermaw --levels 7 --format json
```

The preview resolves dictionary data without opening a game, changing a journey,
or granting rewards. Markdown displays the complete elemental relationship
table and its rationale. CSV includes `element`, all nine `damage_percent_*`
columns, `absorption_elements` and `absorption_healing_percent`; absorption
takes precedence over the corresponding damage column. JSON retains the
complete `metadata.elemental_profile`. Unassigned fixed encounters remain
explicitly unassigned in the authoring output. This tool is for development;
it does not make the data visible during play.

The [Cave Bat review](reviews/cave_bat/README.md) records
the generated entry, combat verification and retained presentation.
