# Character abilities and weapon unlocks

Caelan is a **Spellblade**. He begins unarmed with his established basic magicks. During MQ02, Mira presents his first weapon before the riverbank outing. His only installed gem is Blue (Water). During the Boar fight, his first **Aqua Edge** attempt fails, then he inadvertently releases and learns **Aether Edge**. The smaller sword-focused water spell later in MQ02 remains a deliberate world action. Aqua Edge itself is learned in the Sanctuary cave’s first encounter.

## Character dictionaries

[`assets/abilities/characters.json`](../assets/abilities/characters.json) contains separate `skills`, `spells` and `abilities` dictionaries for Caelan, Mira, Lucan, Rhea and Edran. Definitions reference stable IDs in [`catalog.json`](../assets/abilities/catalog.json) and an unlock:

- `starting`: known from the beginning.
- `first_weapon`: granted by generic weapon acquisition, or held pending by an authored training sequence until its discovery.
- `learned`: granted explicitly and retained in the character's learned history.

The current design identities are Spellblade, Engineer, Armsmaster, Aethermage
and Sage. **Documentation revision, 2026-11-07:** Engineer replaces Machinist
for Mira, and Armsmaster replaces Knight for Lucan. The runtime dictionaries
still contain the earlier Machinist and Knight labels; changing those labels
is a separate implementation task.

Mira starts with Overclock and Rivet; Piston Jab belongs to the bot definition. Registration does not recruit a party member or grant equipment. Focused Strike remains a future explicitly learned skill. `basic_magicks` is an authored-world capability rather than an executable combat skill.

Future combat direction is captured in the character sheets for
[Caelan](narrative/game_01/characters/CAELAN.md#combat-progression-concept),
[Mira](narrative/game_01/characters/MIRA.md#combat-progression-concept) and
[Lucan](narrative/game_01/characters/LUCAN.md#combat-progression-concept).
Further gem, gear, bot, self-augment and weapon unlock methods remain
undecided. Caelan’s implemented acquisitions cover the Blue-gem/Aqua opening
and the optional Red/Flame and White/Ice guardian rewards.

Aqua Edge has a permanent `learned` entry, separate from the failed Boar attempt used to teach Aether Edge. Nature, Fire and Ice techniques are not available in the opening lesson. Selecting or owning a gem does not automatically teach an ability. Optional level-four Embravyr and Nivareth encounters install the Red/Fire and White/Ice gems and teach Flame Edge and Ice Edge respectively, in either order. See [elemental cave encounters](ELEMENTAL_CAVE_ENCOUNTERS.md).

## Mira’s Blade

The owned item is `caelan_gearblade`, displayed as **Mira’s Blade**. Its circular gear guard initially contains only the Blue Water gem; the other sockets are empty. The grip remains still while the ring selects an owned focus. Empty sockets cannot be selected. The item provides no free attribute bonus or elemental mastery. Caelan supplies the control and effort to direct available aether.

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

The root menu includes Skills even when unavailable. Before owning a weapon, it explains **Requires a weapon**. With a pending lesson weapon, MQ02’s guided opening first teaches Guard against the telegraphed charge. His Skills menu then offers only **Aqua Edge**. This attempt sputters without spending MP; the same attempted technique inadvertently follows through as a successful **Aether Edge**, costing its normal 4 MP. There is no second elemental menu selection. Its impact learns Aether Edge and releases ordinary party controls; Aqua Edge remains unlearned until the cave.

During the short guided lesson, actor switching and Flee are unavailable; the game points to Guard, then Skills. Mira covers with Guard, and Rivet contributes bounded autonomous attacks. Once discovery completes, ordinary commands, target selection and Mira’s player-controlled turns return. Opening or closing Skills spends no MP or ATB; ordinary choices pause every gauge. Back/Escape leaves the submenu without accidentally consuming an attempt. Escape at the root pauses battle.

Mira’s Skills contains Overclock. It requires her active bot and 5 MP; it gives Rivet Haste for eight completed bot turns at 1.5× ATB fill, refreshing without stacking. Aether Dart still requires its independent learned unlock. See [Mira’s bot rules](MIRA_BOTS.md).

## Aqua Edge and the first cave encounter

The first Sanctuary cave entrance with Mira’s Blade presents a short saved
resonance scene. Caelan notices concentrated ambient aether and the Blue gem’s
light, then decides to try focusing Aqua Edge again. This scene does not teach
the combat ability by itself.

The normal 16–36-tile distance trigger selects a fixed pair of level-two Cave
Bats for this lesson. Caelan chooses Skills → Aqua Edge. Mira, Rivet and enemy
actions wait until its successful opening strike, so the encounter cannot end
before the lesson. Aqua Edge costs **0 MP throughout this introductory
battle**, including its retries, even if he entered with no MP. After clearing the encounter, ordinary
Aqua Edge normally costs **4 MP** in every area; the cave is not a continuing requirement. The two optional elemental teaching encounters waive every learned elemental Edge's MP cost throughout the battle and retries, while Aether Edge and Overclock retain 4 and 5 MP.

Aqua Edge combines physical potency 1 with **Water** magical potency 0.5. Only
the magical component reads the target’s elemental profile, including its exact
0–200% response or matching-element absorption. The physical component remains
ordinary physical damage. Aether Edge remains available and non-elemental. Flame Edge and Ice Edge
use the same physical potency 1 plus magical potency 0.5, with Fire and Ice
magical components and their matching selected owned gem. Each normally costs
4 MP. The one-time focus victory, rather than selection or a raw material,
teaches its associated technique.

The resonance, learned ability and cleared introductory battle are separate
facts. Discovery checkpoints the earned skill and battle resources immediately.
An unfinished introductory formation keeps its saved seed after withdrawal or
defeat, and retry skips the discovery if already learned. See
[Caelan’s opening progression](CAELAN_AQUA_PROGRESSION.md) for migration and retry
rules.

## Acquisition and saved journeys

[`character_abilities.py`](../character_abilities.py) owns permanent first-weapon history, deferred training, explicitly learned abilities, owned gems and equipped references. The same version-one `character_abilities` envelope accepts optional `deferred_weapon_training: ["caelan"]`; the key is omitted when there is no pending lesson. Old first-weapon history retains its already-known technique. New Game clears history, equipment and deferral. Malformed or unowned equipment is rejected during validation without replacing a journey.

`CharacterAbilities.learn_ability(character_id, ability_id)` grants a registered
`learned` entry explicitly. It does not consume an item or grant unrelated
abilities. An optional `learned_abilities` mapping in the version-one snapshot
preserves these grants. Existing saves import earned abilities into this history;
new games do not receive every registered skill automatically.

Generic `CharacterAbilities.acquire_weapon(character_id, item_id, learn_starter=True)` preserves immediate starter learning. The MQ02 gift uses `learn_starter=False`: the owned weapon and first-weapon receipt exist, but `starter_skills_pending('caelan')` remains true. Reequipping or unequipping cannot bypass that deferral. `learn_first_weapon_skills('caelan')` commits the earned discovery idempotently and requires an owned, equipped weapon; it never grants another item.

`game.equip_weapon(character_id, item_id)` equips an already-owned weapon; `None` unequips it. Unequipping a learned technique retains knowledge but prevents weapon-required use. Equipment reserves inventory quantities across characters, and loadout changes remain blocked during combat.

Older active/completed MQ02 journeys preserve prior progress without replaying the birthday scene. Older active weaponless routes retain their compatibility dialogue. A completed legacy-bypass MQ02 journey that still lacks the blade receives one owned, Blue-only blade and its starter Aether Edge through an idempotent compatibility migration. This records the current story equipment without replaying scenes or restoring resources. New available quests receive the presentation before recruitment. Save/retry paths never duplicate the gift, learned technique or encounter rewards.

Optional guardian victory saves its guaranteed focus item, installed gem,
learned Edge, selected focus, EXP, resources and receipt atomically. The
installation exchange is an acknowledged presentation after Spoils; KO Caelan
receives the focus and skill immediately but waits to acknowledge it until
conscious. Neither guardian is required to obtain the other or defeat
Vespermaw.

Owned gems are saved separately from `gear_focus`. Acquiring Mira’s Blade grants only Water. Raw Aether Sapphire, Ruby or other material drops do not install focus gems. Saves without gem ownership migrate to Blue only, retaining earned Aether Edge and existing character progress. Older journeys with prior cave encounters receive Aqua Edge without replaying a completed introduction.
