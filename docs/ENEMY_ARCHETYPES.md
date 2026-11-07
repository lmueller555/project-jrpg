# Enemy stat profiles and fighting styles

Enemy design combines a **stat profile**, a **fighting style** and an **ability
set**. Level supplies the baseline described in [Leveling](LEVELING.md); the
profile defines numerical strengths and weaknesses, while style defines action
selection, targeting, sequences and reactions. Species, elemental affinities,
potential Stagger properties and normal/elite/boss tuning are additional layers.

The machine-readable catalogue is
[`assets/combat/enemy_archetypes.json`](../assets/combat/enemy_archetypes.json),
loaded by [`enemy_growth.py`](../enemy_growth.py). Its classifications are design
metadata, not twenty implemented enemy AIs. Numeric profile multipliers remain
pending and must not be inferred as an approved uniform multiplier.

## Ten stat profiles

| Profile | Stat priorities and tradeoffs |
| --- | --- |
| **Balanced** | Moderate HP, offenses, defenses and Speed; the reference profile. |
| **Brute** | High HP and Strength; low Speed and weaker magical protection. |
| **Armored** | High Defense and good HP; lower Magick Defense. |
| **Warded** | High Magick Defense; lower physical Defense. |
| **Swift** | High Speed and Accuracy; moderate physical offense and limited durability. |
| **Evasive** | High Evasion; low HP and defenses, with less Speed emphasis than Swift. |
| **Caster** | High Magick and MP; low physical durability. |
| **Hybrid** | Good Strength and Magick, with sufficient MP to alternate damage types. |
| **Support** | High Spirit and MP; low direct offense and respectable magical protection. |
| **Lightweight** | Low HP and modest individual damage; suited to larger groups. |

Multiple enemies already produce more combined ATB actions. Lightweight does
not automatically imply exceptionally high Speed. The intended outcome is a
recognizable role with multiple workable responses, not a requirement to bring
one particular character.

These profiles adjust the common baseline rather than defining ten unrelated
level curves. Exact multipliers are the next numerical design task. Fighting
styles can supply temporary conditional changes, such as a Berserker's low-HP
aggression; permanent profile growth and temporary effects retain separate
ownership.

## Twenty approved enemy concepts

These names preserve the approved encounter concepts. Some primarily describe
stats and others primarily describe behavior. Reusable behavior rules can be
shared across concepts and combined with compatible profiles; a distinct concept
does not require a distinct growth curve or wholly separate AI implementation.

| # | Concept | Combat identity and intended response |
| ---: | --- | --- |
| 1 | **Soldier** | Balanced stats and straightforward attacks. Establishes the ordinary enemy benchmark and supports specialists. |
| 2 | **Brute** | High HP and Strength, low Speed. Prepare between heavy attacks or exploit magical vulnerability. |
| 3 | **Bulwark** | Very high Defense and lower Magick Defense. Favor magic or eliminate dangerous allies first. |
| 4 | **Warder** | Very high Magick Defense and lower Defense. Physical attacks provide an efficient answer. |
| 5 | **Duelist** | High Speed and Accuracy. Frequent, reliable attacks make early elimination valuable. |
| 6 | **Skirmisher** | High Evasion and low durability. Favor accurate attacks over raw power alone. |
| 7 | **Arcanist** | High Magick/MP and fragile defenses. Prioritize physical burst damage and magical protection. |
| 8 | **Battlemage** | Physical and magical attacks challenge reliance on one defensive strength. |
| 9 | **Windup Attacker** | Telegraphs a powerful attack followed by recovery. Guard the threatened character or defeat it before the attack. |
| 10 | **Mender** | Heals allies using Spirit and MP. Concentrate damage, remove the healer, or outlast its finite MP. |
| 11 | **Captain** | Buffs allies. Eliminate the support source before it strengthens the encounter further. |
| 12 | **Berserker** | Becomes more aggressive below an HP threshold. Finish wounded enemies decisively. |
| 13 | **Opportunist** | Favors the living character with the lowest HP percentage. Protect and recover vulnerable teammates. |
| 14 | **Counterfighter** | Telegraphs retaliation against a particular attack category. Change damage type or temporarily switch targets. |
| 15 | **Stancechanger** | Alternates defensive strengths. Adjust attack selection as its stance changes. |
| 16 | **Swarmer** | Weak individuals create collective ATB pressure. Remove members quickly; future area attacks provide another answer. |
| 17 | **Regenerator** | Restores its own HP. Concentrated burst damage overcomes its self-sustain. |
| 18 | **Siphoner** | Drains party MP to replenish its own. Creates resource pressure despite modest HP damage. |
| 19 | **Guardian** | Intercepts limited attacks against selected allies. Defeat it, exhaust protection or attack uncovered targets. |
| 20 | **Disruptor** | Occasionally reduces a target's ATB gauge. Threatens the timing of attacks and recovery. |

Action patterns include straightforward physical or magical offense, mixed
physical/magical alternation, windup/recovery, ally healing, ally buffs,
low-HP aggression, wounded-target selection, retaliation, stance switching,
self-recovery, MP siphoning, interception and ATB disruption. Several concepts
can use the same pattern with different stats or abilities.

Menders and Captains require enemy healing/buff actions and multi-enemy support.
Regeneration, MP transfer, interception, counters, stance changes and ATB reduction
require authored actions or triggers. Evasive and precision-oriented roles also
depend on future hit/evasion resolution. Listing these roles does not enable
those actions in the current encounter controller.

## Current enemy classifications

| Enemy | Stat profile | Fighting style | Species adjustment |
| --- | --- | --- | --- |
| **Bat** | Hybrid | Alternates physical Bite and magical Wing Gust; falls back to Bite when MP is exhausted. | A small Evasion bias; exact growth adjustment pending. |
| **Ridgeback Tusker / Boar** | Brute | Windup Attacker: Lowered Tusks telegraphs Bankbreaker Charge. | Individual encounter and boss tuning pending. |

The Bat's classification describes its mixed damage approach. It does not imply
a humanoid class, and its modest Evasion bias does not make evasion its primary
combat identity. The Tusker's high HP and physical offense provide its numerical
profile; reacting to its charge is the central behavioral lesson.

These references do not retune the live Bat or MQ02 Tusker. Their current
attributes, ability timing, RP and drops remain authored in
[`enemies.json`](../assets/combat/enemies.json) and the battle controller until
profile weights, enemy levels and the progression transition are settled.

## Catalogue and growth API

`load_archetypes()` returns a validated fresh copy of the catalogue. The catalogue
declares `runtime_binding: "metadata_only"`. Each of the ten stat profiles has
`multipliers: null`, making the unresolved numerical weights explicit. Concepts
reference fourteen reusable fighting-style descriptions; their implementation
metadata distinguishes existing patterns from behavior requiring implementation.
Species adjustments for the Bat and Tusker remain `null` as well.

```python
from enemy_growth import baseline_enemy_stats, build_enemy_stats, load_archetypes

baseline_enemy_stats(100)['hp']  # 50000
catalogue = load_archetypes()

# An explicit authoring fixture, not an approved Brute or boss multiplier:
example = build_enemy_stats(100, multipliers={'hp': 2})
assert example['hp'] == 100000
```

`raw_baseline_enemy_stats(level)` exposes the unrounded reference. The builder
applies supplied numerical adjustments before rounding and effective caps;
omitted attributes retain their baseline. It does not interpret a qualitative
profile name as an invented set of numerical weights. Invalid levels, multiplier
values and catalogue references are rejected before producing an enemy record.

## Combinations and future layers

An Armored Mender and a Swift Mender can both heal, but differ in durability and
action frequency. A Caster Counterfighter can retaliate with strong magic. A
Brute can use simple attacks, windup attacks or low-HP aggression.

Useful encounter compositions include Bulwark + Arcanist, Mender + Berserkers,
Captain + Duelists, and Warder + Bulwark. Author compatible combinations and tune
the complete encounter rather than assuming every pairing has equal difficulty.

Elemental affinities provide another answer without replacing the underlying
role. A Water weakness can offer a route through a fire-aligned Bulwark; a Fire
weakness can make the right spell useful against an ice-aligned Warder. Stagger
could later expose a Bulwark's defenses, disrupt a windup or disable a counter
stance. Affinities and Stagger rules are future design, not active catalogue AI.

Elite and boss status remain separate tuning layers. The roughly ten-times boss
XP reference does not require ten-times HP or ten-times every rating.
