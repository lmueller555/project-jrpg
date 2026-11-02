# Character abilities and weapon unlocks

Caelan's job identity is **Spellblade**. He begins unarmed, with his established
basic magicks, and learns **Aether Edge** when he first acquires/equips a weapon.
Aether Edge is his only weapon-granted starter skill. Focused Strike remains an
existing future Lattice unlock; it is neither granted nor made executable here.

## Character dictionaries

[`assets/abilities/characters.json`](../assets/abilities/characters.json) contains
separate `skills`, `spells`, and `abilities` dictionaries for Caelan, Mira, Lucan,
Rhea and Edran. Each entry references a stable ID in the shared
[`catalog.json`](../assets/abilities/catalog.json) and specifies its unlock:

- `starting`: known from the beginning.
- `first_weapon`: permanently known after the first weapon acquisition/equip.
- `lattice`: learned from the character's activated Lattice nodes.

The registered identities are Spellblade, Machinist, Knight, Aethermage and Sage,
respectively. Future companions have empty ability dictionaries until their
abilities are designed. Registration does not recruit anyone, grant equipment
or add commands to Mira's existing guest profile. Caelan's current Lattice
abilities retain their IDs, rewards and unlock requirements.

To add an ability, define its shared name/description/kind, register it in the
appropriate character dictionary, and implement its battle action if applicable.
Catalog registration alone does not make an unimplemented action executable.
`basic_magicks` remains an authored-world capability rather than a combat skill.
Rebuilding Caelan's Lattice preserves shared definitions belonging to weapon
unlocks and other characters; it does not add those abilities as Lattice nodes.

## Aether Edge

| Property | Initial tuning |
| --- | --- |
| Command | Skills → Aether Edge |
| Requirement | Learned skill and an equipped, owned weapon |
| Cost | 4 MP and one normal ATB action |
| Target | Self |
| Cast / effect time | 0.90 / 0.50 seconds |
| Duration | Three subsequent physical weapon strikes in this encounter |
| Effect | Add a non-elemental Mag-based component at potency 0.5 |

The ordinary physical component still uses Str/Def; the added component uses
Mag/M. Def. Both use the same variance roll and existing protection rules. Their
sum is one hit, one damage popup and one shared 9,999 damage cap. This introduces
no elemental affinities or elemental coverage. Recasting refreshes three strikes
without stacking. Spells, Guard and other actors' attacks do not spend charges.
Charges end with the battle and are not saved as a persistent buff.

The existing cast pose, a blue self-enchantment cue and a remaining-strikes label
show activation and duration. Aether Edge does not fire a projectile at an enemy.
Its costs and potency are initial tuning values, kept in
[`assets/combat/actions.json`](../assets/combat/actions.json).

## Combat menu

The root menu includes **Skills** even when unavailable. During Caelan's unarmed
MQ02 boar fight it is greyed out; selecting it explains **Requires a weapon**.
After his weapon unlock, Skills opens a submenu containing Aether Edge and Back.
Opening or closing the submenu spends no MP or ATB and leaves all gauges paused.
Back or Escape returns to the root; Escape at the root pauses the battle.
Switching ready characters or beginning another turn resets the submenu.

Mira retains her stronger short-spear attack and has no new skills. Existing
Aether Dart access still requires its Lattice unlock and remains independent
of weapon equipment.

## Acquisition and saved journeys

[`character_abilities.py`](../character_abilities.py) owns permanent first-weapon
history and equipped weapon references. Game checkpoints it under
`character_abilities` together with inventory and Lattice state. Older journeys
without this record continue unarmed with no automatic weapon-skill unlock.
New Game clears the history. Malformed or unowned equipment is rejected during
save validation without replacing an existing journey.

Future story acquisition calls `game.acquire_weapon('caelan', item_id)` with a
real weapon ID from the item catalog. This adds/equips the weapon and learns
Aether Edge in one operation. `game.equip_weapon(character_id, item_id)` equips
an already owned weapon; `None` unequips it. Unequipping retains the permanent
unlock but prevents using Aether Edge. Equipment reserves owned item quantities
across characters. Loadout changes are blocked during combat.

There is currently no weapon item or scripted weapon-acquisition scene in the
opening content. This foundation supplies that future scene's grant hook; it
does not give Caelan a weapon before the boar fight or add an acquisition quest.

The [combat UI review](reviews/character_skills/README.md) contains production
screenshots and regression evidence, with its test-only weapon clearly labeled.
