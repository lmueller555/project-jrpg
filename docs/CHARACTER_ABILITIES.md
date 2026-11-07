# Character abilities and weapon unlocks

Caelan is a **Spellblade**. He begins unarmed with his established basic magicks. During MQ02, Mira presents his first weapon before the riverbank outing. His first attempted elemental technique fails; his next attempt produces **Aether Edge**, his only learned starter skill. The smaller sword-focused water spell later in the quest is a deliberate world action, not an Aqua Edge unlock.

## Character dictionaries

[`assets/abilities/characters.json`](../assets/abilities/characters.json) contains separate `skills`, `spells` and `abilities` dictionaries for Caelan, Mira, Lucan, Rhea and Edran. Definitions reference stable IDs in [`catalog.json`](../assets/abilities/catalog.json) and an unlock:

- `starting`: known from the beginning.
- `first_weapon`: granted by generic weapon acquisition, or held pending by an authored training sequence until its discovery.
- `lattice`: learned from an activated Lattice node.

The current design identities are Spellblade, Engineer, Armsmaster, Aethermage
and Sage. **Documentation revision, 2026-11-07:** Engineer replaces Machinist
for Mira, and Armsmaster replaces Knight for Lucan. The runtime dictionaries
still contain the earlier Machinist and Knight labels; changing those labels
is a separate implementation task.

Mira starts with Overclock and Rivet; Piston Jab belongs to the bot definition. Registration does not recruit a party member or grant equipment. Focused Strike remains a future Lattice unlock. `basic_magicks` is an authored-world capability rather than an executable combat skill.

Future combat direction is captured in the character sheets for
[Caelan](narrative/game_01/characters/CAELAN.md#combat-progression-concept),
[Mira](narrative/game_01/characters/MIRA.md#combat-progression-concept) and
[Lucan](narrative/game_01/characters/LUCAN.md#combat-progression-concept).
Their gem, gear, bot, self-augment and weapon unlock methods are undecided;
these concepts do not choose the Aether Lattice or its eventual replacement.

Nature Edge, Aqua Edge and Flame Edge have shared catalog definitions for the first lesson. They are temporary attempts, not permanent entries in Caelan’s learned dictionary. The visible white Ice gem does not add an initial Ice Edge command. After the breakthrough, only Aether Edge remains usable until later progression grants other abilities.

## Mira’s Blade

The owned item is `caelan_gearblade`, displayed as **Mira’s Blade**. Its circular gear guard holds four focus gems: green Nature, blue Water, red Fire and white Ice. The grip remains still while the ring selects a focus. The item provides no free attribute bonus or elemental mastery. Caelan supplies the control and effort to direct available aether.

The workshop gift presentation shows the whole blade, handoff, selector and the friends’ reactions with the standard portrait text panel. It grants and equips the item once after acknowledgment. It does not demonstrate a successful elemental spell or immediately expose Aether Edge.

## Aether Edge

| Property | Initial tuning |
| --- | --- |
| Command | Skills → Aether Edge |
| Requirement | Learned technique and an equipped, owned weapon |
| Cost | 4 MP and one normal ATB action |
| Target | One enemy |
| Duration / impact | 2.00 / 1.00 seconds (full choreographed action) |
| Effect | Immediate physical strike at potency 1 plus non-elemental Mag component at potency 0.5 |

The physical component uses Str/Def and the magical component uses Mag/M. Def. They share the same variance roll and combine into one hit, one damage popup and one 9,999 per-hit cap. The action does not grant charges, enchant later attacks, fire a projectile or introduce elemental affinities. This deliberately replaces the older three-strike self-enchantment.

The accidental tutorial strike uses the same actual action. It is discovered on the resolved attack’s impact, not on opening Skills or selecting Back. The battle immediately exposes the learned technique; world persistence records the discovery so withdrawal/retry does not repeat it. Costs and potency live in [`assets/combat/actions.json`](../assets/combat/actions.json).

## Combat menu and first lesson

The root menu includes Skills even when unavailable. Before owning a weapon, it explains **Requires a weapon**. With a pending lesson weapon, MQ02’s guided opening first teaches Guard against the telegraphed charge. Caelan’s first skill turn offers Nature Edge, Aqua Edge and Flame Edge; all fail, consuming the ATB turn without an MP penalty. On his **next full ATB**, any of those choices resolves as Aether Edge. The temporary entries disappear, and normal party controls resume with Aether Edge as the only learned starter technique.

During the short guided lesson, actor switching and Flee are unavailable; the game points to Guard, then Skills. Mira covers with Guard, and Rivet contributes bounded autonomous attacks. Once discovery completes, ordinary commands, target selection and Mira’s player-controlled turns return. Opening or closing Skills spends no MP or ATB; ordinary choices pause every gauge. Back/Escape leaves the submenu without accidentally consuming an attempt. Escape at the root pauses battle.

Mira’s Skills contains Overclock. It requires her active bot and 5 MP; it gives Rivet Haste for eight completed bot turns at 1.5× ATB fill, refreshing without stacking. Aether Dart still requires its independent Lattice unlock. See [Mira’s bot rules](MIRA_BOTS.md).

## Acquisition and saved journeys

[`character_abilities.py`](../character_abilities.py) owns permanent first-weapon history, deferred training and equipped references. The same version-one `character_abilities` envelope accepts optional `deferred_weapon_training: ["caelan"]`; the key is omitted when there is no pending lesson. Old first-weapon history retains its already-known technique. New Game clears history, equipment and deferral. Malformed or unowned equipment is rejected during validation without replacing a journey.

Generic `CharacterAbilities.acquire_weapon(character_id, item_id, learn_starter=True)` preserves immediate starter learning. The MQ02 gift uses `learn_starter=False`: the owned weapon and first-weapon receipt exist, but `starter_skills_pending('caelan')` remains true. Reequipping or unequipping cannot bypass that deferral. `learn_first_weapon_skills('caelan')` commits the earned discovery idempotently and requires an owned, equipped weapon; it never grants another item.

`game.equip_weapon(character_id, item_id)` equips an already-owned weapon; `None` unequips it. Unequipping a learned technique retains knowledge but prevents weapon-required use. Equipment reserves inventory quantities across characters, and loadout changes remain blocked during combat.

Older active/completed MQ02 journeys preserve prior progress without a forced retroactive birthday scene. Their weaponless route uses compatibility dialogue rather than claiming a gift or elemental discovery that did not occur. New available quests receive the presentation before recruitment. Save/retry paths never duplicate the gift, learned technique or encounter rewards.
