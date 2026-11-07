# Bestiary dictionary

[`assets/combat/bestiary.json`](../assets/combat/bestiary.json) is the canonical
dictionary for monster and boss definitions. Entries are keyed by stable enemy
IDs under `enemies`. [`bestiary.py`](../bestiary.py) validates the complete
dictionary and resolves a species at an explicitly selected level.

The dictionary contains the first computed species, **Cave Bat**, and preserves
the existing fixed Bat and Ridgeback Tusker records for their authored test and
MQ02 encounters. Fixed records retain their exact stats, abilities and item
drops. Their future levels, species tuning and elemental profiles have not been
assigned.

This is an authoring dictionary and combat adapter. It does not add a
player-facing encyclopedia menu, unlock the sanctuary cave, place new world
encounters, or activate saved character levels and combat XP grants.

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
| XP reward | 84 | 104 |

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

The Cave Bat's elemental profile is authored below. Applying elemental damage
and absorption in battle remains future work, as does its planned low Stagger
resistance. Item drops remain explicitly pending; the resolved combat bundle is
empty until loot is authored. No item or drop chance is invented by the loader.

## Elemental identity and relationships

The canonical roster is **Non-Elemental, Fire, Electric, Water, Ice, Nature,
Wind, Holy and Ground**. Nature replaces the proposed Poison element and keeps
Caelan's existing Nature gem within the roster. Poison status, if introduced,
is separate from an elemental damage type.

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
This data update does not implement Study, add automatic HUD affinity labels or
apply elemental combat effects.

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
assert bat['xp_reward'] == 84
assert bat['metadata']['drops_pending']
assert bat['metadata']['elemental_profile']['element'] == 'non_elemental'
assert bat['metadata']['elemental_profile']['damage_percentages']['fire'] == 200

fixed = build_enemy('bat')
assert fixed['combat']['attributes']['hp'] == 72
assert fixed['level'] is None
assert fixed['xp_reward'] is None
```

`load_bestiary(data=None, actions=None)` returns a validated, detached dictionary.
An optional `actions` argument supplies an already validated action dictionary.
`build_enemy(enemy_id, level=None, *, data=None, actions=None)` returns a fresh
resolved record containing `id`, `level`, `xp_reward`, `combat`,
`fighting_style`, `behavior`, `presentation` and `metadata`.

The `combat` block contains exactly `name`, `attributes`, `abilities` and
`rewards`, compatible with the existing battle validator. Elemental design is
retained in `metadata['elemental_profile']`; it is not a combat modifier yet.
Behavior, presentation and future-mechanic information retain separate ownership. Species require an
explicit level within their authored range; fixed records accept no level.
Unknown IDs, malformed ranges, invalid references, non-finite multipliers and
missing free fallback actions are rejected.

```python
from battle_model import BattleModel
from character_attributes import CharacterAttributes

model = BattleModel.from_bestiary(CharacterAttributes(), 'cave_bat', 2)
assert model.enemy.name == 'Cave Bat'
assert model.enemy_level == 2
assert model.enemy_xp_reward == 84
assert model.enemy_sprite_id == 'bat'
```

`BattleModel.from_bestiary(player_attributes, enemy_id, level, *,
bestiary_data=None, **options)` exposes the resolved metadata through
`enemy_bestiary_id`, `enemy_level`, `enemy_xp_reward`, `enemy_sprite_id` and
`enemy_action_aliases`, plus the detached `enemy_bestiary_record`. These values
do not award XP or serialize a new world
encounter. Unsupported future fighting styles remain data until their action
selection and behavior are implemented; the combat adapter rejects them rather
than silently substituting another style.

## Adding another monster or boss

1. Copy the computed Cave Bat entry under a new stable ID. Retain
   `"mode": "species"` and author its name, description, family, habitats and
   inclusive `level_range` (`min` and `max`).
2. Select an approved stat profile and combat concept, then supply explicit
   `species_multipliers` and `tier_multipliers`. Omitted attribute factors are
   ×1. Keep the common growth curve in the growth backend.
3. Register any new action definitions in
   [`actions.json`](../assets/combat/actions.json), then reference their IDs in
   the sequence and free fallback. Choose a supported targeting policy and
   fighting style, or implement the missing behavior before battle use.
4. Author a complete `elemental_profile`, including all nine damage percentages,
   matching-element absorption and a rationale for the clues players can infer.
   Consider identity early enough to inform the monster's name, visual design,
   habitat and behavior. Keep the data hidden except through deliberate reveal
   mechanics such as the planned Study ability.
5. Author presentation references and explicitly mark future mechanics and
   undecided drops. Reusing art is independent of gameplay action identity.
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
