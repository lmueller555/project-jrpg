# Enemy stat profiles and fighting styles

Enemy design combines a **stat profile**, a **fighting style** and an **ability
set**. Level supplies the baseline described in [Leveling](LEVELING.md); the
profile defines numerical strengths and weaknesses, while style defines action
selection, targeting, sequences and reactions. Species, elemental affinities,
potential Stagger properties and normal/elite/boss tuning are additional layers.

The machine-readable catalogue is
[`assets/combat/enemy_archetypes.json`](../assets/combat/enemy_archetypes.json),
loaded by [`enemy_growth.py`](../enemy_growth.py). Its classifications are design
metadata, not twenty implemented enemy AIs. The ten stat profiles now have
approved, executable numerical multipliers. Enemy levels, species adjustments
and elite/boss tuning remain separate authoring work.

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
level curves. Apply the following multipliers at every level:

| Profile | HP | MP | STR | MAG | SPR | DEF | M. DEF | Speed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Balanced | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| Brute | 1.50 | 0.50 | 1.15 | 0.60 | 0.75 | 1.10 | 0.75 | 0.75 |
| Armored | 1.25 | 0.75 | 0.90 | 0.75 | 0.90 | 1.60 | 0.60 | 0.80 |
| Warded | 1.10 | 1.25 | 0.90 | 0.90 | 1.10 | 0.65 | 1.60 | 0.90 |
| Swift | 0.80 | 0.75 | 1.00 | 0.75 | 0.75 | 0.85 | 0.85 | 1.40 |
| Evasive | 0.70 | 0.75 | 0.90 | 0.90 | 0.75 | 0.75 | 0.85 | 1.15 |
| Caster | 0.75 | 1.50 | 0.50 | 1.20 | 1.00 | 0.65 | 1.10 | 0.90 |
| Hybrid | 0.95 | 1.15 | 1.05 | 1.05 | 0.80 | 0.90 | 0.90 | 1.00 |
| Support | 1.00 | 1.50 | 0.55 | 0.60 | 1.35 | 0.90 | 1.15 | 1.00 |
| Lightweight | 0.40 | 0.50 | 0.65 | 0.65 | 0.60 | 0.70 | 0.70 | 1.00 |

Accuracy, Evasion and Luck use **1.00** except **Swift Accuracy 1.20** and
**Evasive Evasion 1.50**. These adjust ratings, not hit, dodge or critical
percentages. The machine-readable data stores all eleven values for every
profile. Lightweight retains ordinary Speed because groups already produce
more combined actions.

Multiply the unrounded baseline by the profile, species and tier factors before
rounding once and applying effective caps. For example, level-100 baseline
Defense is 287.5 before display rounding. Armored Defense is therefore
`round_half_up(287.5 × 1.60) = 460`, not a multiplication of the displayed 288.

| Profile | Selected level-100 results, before species/tier adjustments |
| --- | --- |
| Brute | HP 75,000; Strength 293; Speed 95 |
| Armored | HP 62,500; Defense 460; Magick Defense 174 |
| Warded | HP 55,000; Defense 187; Magick Defense 464 |
| Swift | HP 40,000; Speed 177; Accuracy 324 |
| Evasive | HP 35,000; Evasion 319 |
| Caster | HP 37,500; Magick 321; MP 803 |
| Support | HP 50,000; Spirit 368; MP 803 |
| Lightweight | HP 20,000; Strength 166; Magick 174 |

Offensive bonuses are deliberately modest because the current damage formula
squares offense: Strength ×1.15 gives about 32% more physical damage at equal
potency and defense, while Magick ×1.20 gives 44% more magical damage. Exact
encounter difficulty still depends on ability potency, cadence, enemy count and
party capabilities. Evasion needs tuning alongside the eventual hit formula;
defensive differences need checking when attacks approach the damage cap.

Fighting styles can supply separately authored temporary changes, such as a
Berserker's low-HP aggression. A style does not automatically add another
permanent stat multiplier.

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
attributes, ability timing and drops remain authored in
[`bestiary.json`](../assets/combat/bestiary.json) and the battle controller until
enemy levels, species adjustments and the progression transition are settled.

The first computed species is **Cave Bat**, separate from the fixed test Bat.
It uses Hybrid growth, Physical/Magical Alternation, levels 2–3 and species
factors HP ×0.40, MP ×0.10 and Evasion ×1.20. **Lithrusk** adds an Armored
Bulwark at levels 2–3 with HP ×0.50 and MP ×0; **Veylume** adds a Caster
Arcanist at levels 3–4 with HP ×0.40 and MP ×0.15. Their presentation is
pending, and Veylume's Magical Offense style remains authored future behavior.
The complete definitions and normal/boss authoring workflow are documented
in the [Bestiary guide](BESTIARY.md).

## Catalogue and growth API

`load_archetypes()` returns a validated fresh copy of the catalogue. The catalogue
declares `runtime_binding: "metadata_only"`, indicating that these data do not
automatically replace live encounter AI or authored stats. Each stat profile has
a complete approved eleven-stat `multipliers` dictionary. Concepts
reference fourteen reusable fighting-style descriptions; their implementation
metadata distinguishes existing patterns from behavior requiring implementation.
Species adjustments for the Bat and Tusker remain `null` as well.

```python
from enemy_growth import (baseline_enemy_stats, build_enemy_stats, load_archetypes,
                          profile_enemy_stats, profile_multipliers)

baseline_enemy_stats(100)['hp']  # 50000
catalogue = load_archetypes()
profile_multipliers('swift')['acc']  # 1.20
profile_enemy_stats('brute', 100)['hp']  # 75000
profile_enemy_stats('armored', 100)['def']  # 460

# An explicit authoring fixture, not an approved boss multiplier:
example = profile_enemy_stats('brute', 100, tier_multipliers={'hp': 2})
assert example['hp'] == 150000
```

`profile_multipliers(profile_id)` returns a fresh copy of the approved weights.
`profile_enemy_stats(profile_id, level, *, species_multipliers=None,
tier_multipliers=None)` combines those weights with optional sparse authoring
adjustments. Omitted adjustment attributes use ×1. Species and tier factors are
explicit; no default boss HP multiplier is inferred from the XP rule.

`raw_baseline_enemy_stats(level)` exposes the unrounded reference, and the
existing `build_enemy_stats(level, *, multipliers)` remains available for direct
explicit authoring. Both builders round after composition and apply caps once.
Invalid levels, profile IDs, weights and catalogue references are rejected.

Use `python tools/preview_leveling.py --enemy-profiles --all-levels --format csv`
to inspect all profiles. The [profile review](reviews/enemy_stat_profiles/README.md)
contains reproducible curve exports and validation.

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
