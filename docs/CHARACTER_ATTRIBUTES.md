# Character attributes

Caelan's attributes are available through **Pause → Characters**. Every
attribute has its own icon. Hover an icon or stat card to see a tooltip naming
the attribute and explaining its effect. Keyboard selection provides the same
information in the description panel. The screen uses the shared interface
style and text-size settings and returns to the pause menu when closed.

## Attribute definitions and starting values

The eleven attributes are shared gameplay definitions. Caelan starts as a
balanced all-rounder, with full HP and MP and equal ratings in the other nine
attributes.

| ID | Display | Caelan starts with | Role |
| --- | --- | --- | --- |
| `hp` | HP | 140 | Maximum health before incapacitation. |
| `mp` | MP | 30 | Maximum energy available for abilities that consume MP. |
| `str` | Str | 10 | Power of physical attacks and techniques. |
| `mag` | Mag | 10 | Power of damaging spells. |
| `spr` | Spr | 10 | Power of healing spells. |
| `def` | Def | 10 | Reduction of incoming physical damage. |
| `m_def` | M. Def | 10 | Reduction of incoming magical damage. |
| `speed` | Speed | 10 | When the character acts in combat. |
| `acc` | Acc | 10 | Chance to land attacks that check accuracy. |
| `eva` | Eva | 10 | Chance to avoid attacks that can be evaded. |
| `lck` | Lck | 10 | Critical-hit chance for attacks that can critically hit. |

**Spirit powers healing; Magick powers damaging spells.** Protective effects
will receive explicit rules when their abilities are designed. The attribute
set does not assign those effects to either stat by implication.

HP and MP values in the attribute record are maxima. Current HP and MP are
separate resources and begin at 140/140 and 30/30. Incapacitation is a gameplay
condition; it does not establish that ordinary combat recovery resurrects the
dead.

The other values are ratings. For example, Acc 10, Eva 10 and Lck 10 do not mean
10% accuracy, evasion or critical chance. Accuracy, evasion and critical-chance
formulas remain future work. Speed now controls the
[ATB gauge's charging rate](COMBAT.md#timing-and-decisions).
Speed does not change exploration walking or running. These starting numbers
are a tunable baseline for the all-rounder profile.

## Attribute caps

| Attribute | Maximum effective value |
| --- | ---: |
| HP | 9,999 |
| MP | 999 |
| Speed | 255 |
| Str, Mag, Spr, Def, M. Def, Acc, Eva, Lck | 999 |

The backend applies these limits to the sum of base attributes and all named
modifier sources. A gain that crosses a limit stops at that limit. For example,
998 Str plus a +4 reward produces 999 Str. Earned bonuses remain recorded by
their owners, so rebuilding modifiers or continuing a journey never stacks or
discards those grants.

Changes to maximum HP/MP leave current resources unchanged unless a caller
explicitly applies a recovery rule. Removing a modifier that would leave current
HP or MP above its new effective maximum is rejected atomically.

Base profiles and saved base values must fit their attribute-specific limits.
Invalid records and current-resource writes are rejected without changing live
state. The separate 999,999 integer bound remains a storage-validation limit
for raw bonuses and sums, rather than a gameplay maximum.

## Runtime and data

[`assets/characters/attributes.json`](../assets/characters/attributes.json)
contains the ordered definitions, display labels, descriptions and Caelan's
starting profile. [`character_attributes.py`](../character_attributes.py)
owns the character's attribute values and current resources independently of
the Characters interface. Each instance has its own state.

The game initializes Caelan's profile when it starts. New Game restores the
starting values and fills both resources. The read-only Characters screen shows
Caelan's portrait, name and live values; opening,
inspecting or closing it does not alter them. Caelan is the currently available
character.

The standalone [traditional leveling foundation](LEVELING.md) defines approved
level-1 profiles and level-100 targets for Caelan, Mira, Lucan, Rhea and Edran.
Its curves leave ordinary natural ratings at or below 300, with slower Speed
growth; the effective caps above leave room for later modifiers. Its allocation
helper gives full XP to surviving active combatants and none to reserves or KO'd
members. `apply_growth(gains)` adds validated nonnegative base-stat gains without
restoring current HP/MP or changing named modifiers. Maximum-resource increases
leave current values unchanged, including zero HP. The live party guest and
placeholder profiles retain their authored ratings until level integration and
recruitment rules are settled.

[`attribute_icons.py`](../attribute_icons.py) draws eleven distinct icons with
the shared interface painter. The icon shapes remain readable on parchment and
on the selected stat card. Tooltip placement follows the logical interface
coordinates, including letterboxed windows and enlarged text.

## Journey compatibility

Journey checkpoints include a version-three `character_attributes` record
containing the character identity, preserved base values under `attributes`,
and current HP and MP. Named modifiers have separate owners. Validation rejects
malformed or out-of-range values before replacing live state, and current
resources must remain within their effective maxima.

Older journeys without the record receive Caelan's starting profile when
continued. Their quest facts, dialogue history and location are preserved.
Subsequent checkpoints include the new record.

Version-one records with Caelan's original 300 maximum HP migrate to the
140-HP starting baseline when continued. Current HP retains its proportion of
the old maximum, rounded to the nearest integer. Zero HP remains zero; a
previously positive value remains at least one. MP and every other attribute
are preserved. Version-one records with a different maximum HP retain that
value, preserving saved growth. Version-two saved ratings become the preserved
base without changing their values.

Retired progression-backed version-three saves import paid attribute bonuses
into capped base values once, including matching party records. Learned
abilities and once-only battle receipts move to their independent owners.
Current resources remain saved values and are not automatically refilled.
No retired score is converted into traditional XP.

Loading the title screen validates a save without changing it. Migration is
committed only when the player continues the journey.

## Scope and story continuity

The approved [damage formula](DAMAGE_FORMULA.md) is implemented in
[`combat_damage.py`](../combat_damage.py). Physical attacks use Str/Def and
damaging magicks use Mag/M. Def, with per-hit limits of 9,999 or 99,999 when
cap-breaking is enabled. The calculator reads effective capped attributes and
does not change the character or their resources.

The first [Bat encounter](COMBAT.md) implements charging, turns and a small set
of actions using this backend. Wider enemy profiles, equipment behavior, healing,
hit/evasion and critical-chance formulas, and the remaining abilities await later
passes. The
attributes do not assign jobs or establish additional playable party members.

Opening quest magicks remain authored actions. Caelan's inability to apply
sustained force against the irrigation current and his small success at the
mill remain intact. Existing scenes do not gain numerical attribute checks,
MP costs or random spell failure.
