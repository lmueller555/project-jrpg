# Character attributes

Caelan's attributes are available through **Pause → Status**. Select an
attribute to read its description. The screen uses the shared interface style
and text-size settings and returns to the pause menu when closed.

## Attribute definitions and starting values

The eleven attributes are shared gameplay definitions. Caelan starts as a
balanced all-rounder, with full HP and MP and equal ratings in the other nine
attributes.

| ID | Display | Caelan starts with | Role |
| --- | --- | --- | --- |
| `hp` | HP | 300 | Maximum health before incapacitation. |
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
separate resources and begin at 300/300 and 30/30. Incapacitation is a gameplay
condition; it does not establish that ordinary combat recovery resurrects the
dead.

The other values are ratings. For example, Acc 10, Eva 10 and Lck 10 do not mean
10% accuracy, evasion or critical chance. Numerical formulas, balance caps and
the effect of Speed on turn frequency remain part of future combat design.
Speed does not change exploration walking or running. These starting numbers
are a tunable baseline for the all-rounder profile.

## Runtime and data

[`assets/characters/attributes.json`](../assets/characters/attributes.json)
contains the ordered definitions, display labels, descriptions and Caelan's
starting profile. [`character_attributes.py`](../character_attributes.py)
owns the character's attribute values and current resources independently of
the status interface. Each instance has its own state.

The game initializes Caelan's profile when it starts. New Game restores the
starting values and fills both resources. The read-only status screen shows
the live values; opening or closing it does not alter them.

## Journey compatibility

Journey checkpoints include an independently versioned
`character_attributes` record containing the character identity, attribute
values and current HP and MP. Validation rejects malformed or out-of-range
values before replacing live state. Resources must remain within their saved
maxima.

Older journeys without the record receive Caelan's starting profile when
continued. Their quest facts, dialogue history and location are preserved.
Subsequent checkpoints include the new record. Continue restores saved
resources rather than automatically refilling them.

## Scope and story continuity

This foundation adds the attribute definitions, starting profile, state
persistence and a status screen. Battle rules, equipment modifiers, damage and
healing formulas, ability costs and Sphere Grid progression remain future
work. The attributes do not assign jobs or establish additional playable party
members.

Opening quest magicks remain authored actions. Caelan's inability to apply
sustained force against the irrigation current and his small success at the
mill remain intact. Existing scenes do not gain numerical attribute checks,
MP costs or random spell failure.
