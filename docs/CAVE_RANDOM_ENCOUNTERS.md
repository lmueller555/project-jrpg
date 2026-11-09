# Sanctuary cave random encounters

Random encounters apply only to the continuous Elden Vale Sanctuary cave.
The roster and spatial rules live in
[`assets/combat/cave_encounters.json`](../assets/combat/cave_encounters.json);
[`cave_random_encounters.py`](../cave_random_encounters.py) owns the durable
distance countdown and random selection. The existing world remains one scene.

## Walking and selection

A triangular roll chooses the next distance from **16–36 tile lengths**, with
**26** as the mode. At 24 pixels per tile these values are 384, 864 and 624
pixels. Actual collision-resolved player movement spends this budget.
Running and walking cover the same budget per distance; diagonals use their
actual length. Standing, blocked movement, followers and scene placement do
not spend it. Movement traces preserve exact trigger positions across frame
rates, including when a frame crosses an area or safe boundary.

Menus, dialogue, scripted movement, transitions, focus loss and safe areas
pause the countdown. Entering another room preserves it. The protected areas
are the entrance apron, High Overlook, Quiet Shelf and Echo Chamber; leaving
protection ensures at least four tile lengths remain. Victory and fleeing roll
a fresh distance. Defeat uses the existing optional-battle withdrawal policy,
returns the entry resources without a reward and also rolls a fresh distance.

The counter saves its remaining distance, rolled threshold, compact random
state and selected encounter ticket. Ordinary Continue and cave reentry do not
reroll an encounter. The ticket fixes formation, levels, battlefield, combat
seed, receipt and return position before the battle-entry cutscene. Continue
from an unfinished battle retries the same encounter with the entry resources.
Old saves without this optional block begin with a fresh counter.

## Encounter roster

Outer covers the entrance and Vein Gallery. Middle covers the grotto, Upper
Passage, Splitstone Hollow and Keeper's Recess. Deep covers Deep Passage and
Deep Gallery. Room polygons and explicit route bands select these pools;
the configuration validates coverage rather than guessing through walls.

| Formation | Outer | Middle | Deep |
| --- | ---: | ---: | ---: |
| Cave Bat | 35% | 20% | 18% |
| Lithrusk | 20% | 15% | 10% |
| Veylume | 0% | 5% | 7% |
| 2 Cave Bats | 30% | 20% | 17% |
| Cave Bat + Lithrusk | 15% | 20% | 13% |
| Cave Bat + Veylume | 0% | 10% | 10% |
| Lithrusk + Veylume | 0% | 0% | 5% |
| 3 Cave Bats | 0% | 5% | 6% |
| 2 Cave Bats + Lithrusk | 0% | 3% | 5% |
| 2 Cave Bats + Veylume | 0% | 1% | 3% |
| Cave Bat + Lithrusk + Veylume | 0% | 1% | 1% |
| 4 Cave Bats | 0% | 0% | 3% |
| 3 Cave Bats + Lithrusk | 0% | 0% | 1% |
| 3 Cave Bats + Veylume | 0% | 0% | 1% |

Columns total 100%. The deeper pool gives 35% singles, 45% pairs, 15% trios
and 5% quartets. A formation contains at most one Lithrusk and one Veylume.
Outer Bats/Lithrusks are level 2. Middle Bats/Lithrusks are level 2–3 and
Veylumes level 3. Deep Bats/Lithrusks are level 3 and Veylumes level 3–4.

## Entry, combat and return

Entry briefly focuses the real exploration frame on the party, then presents
an actual loading screen. Only after that screen has been drawn does the
controller construct combatants, load sprite banks and prepare the selected
battlefield. A short reveal opens combat. Escape/focus loss pauses entry and
held inputs cannot carry through to spend a combat turn. Loading or checkpoint
failures offer retry while retaining the same ticket.

Four native asset-pack battlefields represent the outer galleries, Reflecting
Grotto, Splitstone Hollow and Deep Gallery. Each has 24 frames over a six-second
cycle, pulsing wall microcrystals and a static reduced-motion frame. The grotto
adds water and drips. A cached renderer frames the scenery for the visible
combat floor at different UI sizes.

`BattleModel.from_bestiary_group` supports one to four independent enemies.
Each living party member, enemy and active bot receives an independent uniform
0–50% starting ATB roll for normal battles. Opening enemy target cycles are
spread across living party members. The scripted first-weapon lesson retains
its authored opening. Each enemy owns its HP, MP, action sequence and charge
target; victory requires defeating all enemies.

For groups, Attack and offensive skills open target selection. Arrow keys and
Enter select/confirm a living foe, Escape returns to commands, and enemy cards
or bodies are clickable. Cards show distinct names, HP and ATB; duplicate Bats
receive distinguishing labels. Bots and attacks retarget defeated enemies.
The single-enemy controls remain available for existing encounters.

Victory resources and reward receipts are checkpointed before returning to
the exact cave position. Continue can resume pending or already-awarded spoils
without repeating grants. Cave victories preserve KO party members and do not
restore HP/MP. Failed return checkpoints roll back the counter/resources so
retry cannot consume another random roll. Fleeing preserves spent resources.
The pending MQ03 outing, escorts, treasures and Kindled Courage ownership
remain intact, including through cave victory and spoils.

Cave entry temporarily switches the soundtrack to Kindled Courage. Victory,
fleeing and defeat fade the previous track back in at its interrupted playback
position; results and Spoils keep that resumed stream. If MQ03 already owns
Kindled Courage, the same stream continues through entry and return.

Enemy stats, XP curves, damage formulas, affinities and item-drop definitions
are unchanged. Group XP is exposed as Bestiary metadata; the existing reward
pipeline still settles item receipts, with live saved-level/XP activation
remaining separate progression work. The three cave species currently have
pending item drops, so their resolved drop bundles are empty. Elemental damage
effects, Stagger, the miniboss and its story resolution remain separate work.

## Validation

```sh
python tools/build_cave_battlefields.py --check
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m pytest -q \
  tests/test_cave_random_encounters.py tests/test_random_enemy_groups.py \
  tests/test_cave_random_gameplay.py
```

The earlier all-treasure traversal test isolates encounter eligibility to
verify geometry, followers and discoveries. The new integration suite walks
through real random entry, loading, grouped combat and persistent return.
