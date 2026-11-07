# Bestiary dictionary

[`assets/combat/bestiary.json`](../assets/combat/bestiary.json) is the canonical
dictionary for monster and boss definitions. Entries are keyed by stable enemy
IDs under `enemies`. [`bestiary.py`](../bestiary.py) validates the complete
dictionary and resolves a species at an explicitly selected level.

The dictionary contains the first computed species, **Cave Bat**, and preserves
the existing fixed Bat and Ridgeback Tusker records for their authored test and
MQ02 encounters. Fixed records retain their exact stats, abilities and item
drops. Their future levels and species tuning have not been assigned.

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

Fire weakness ×2 and low Stagger resistance are planned metadata. They do not
change damage or timing until those mechanics are implemented. All other
elemental affinities are neutral. Item drops remain explicitly pending; the
resolved combat bundle is empty until loot is authored. No item or drop chance
is invented by the loader.

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
`rewards`, compatible with the existing battle validator. Behavior, presentation
and future-mechanic information retain separate ownership. Species require an
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
4. Author presentation references and explicitly mark future mechanics and
   undecided drops. Reusing art is independent of gameplay action identity.
5. Preview every level in the range and test the resolved combat behavior.

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
or granting rewards. The [Cave Bat review](reviews/cave_bat/README.md) records
the generated entry, combat verification and retained presentation.
