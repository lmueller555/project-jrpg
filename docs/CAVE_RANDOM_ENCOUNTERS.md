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
are the entrance apron, High Overlook, Quiet Shelf, Echo Chamber, the two
guardian chambers and their final approaches; earlier branch stretches retain
their outer or deep random pools. Leaving
protection ensures at least four tile lengths remain. Ordinary victory and
fleeing roll a fresh distance. Party defeat opens Game Over without changing
saved resources or the encounter countdown. Loading restores the chosen snapshot.
The introductory Aqua lesson has special withdrawal behavior:
its exact pending bat-pair ticket remains after withdrawal until
victory, with a deferred retry that allows travel and preparation.

The counter saves its remaining distance, rolled threshold, compact random
state and selected encounter ticket. Ordinary Continue and cave reentry do not
reroll an encounter. The ticket fixes formation, levels, battlefield, combat
seed, receipt and return position before the battle-entry cutscene. Continue
from an unfinished battle retries the same encounter with the entry resources.
Old saves without this optional block begin with a fresh counter.

## First-encounter lesson

The first entrance with Mira’s Blade acknowledges a separate Blue-gem
resonance scene. The first distance trigger then fixes **two level-two Cave
Bats**, regardless of the local weighted pool. The saved ticket identifies the
Aqua lesson, retaining the formation, battlefield, seed and return position.
Enemy, Mira actions wait for Caelan’s successful player-selected Aqua
Edge. The successful opening strike learns Aqua Edge at impact; ordinary ATB
combat follows. Aqua Edge costs **0 MP throughout this encounter and its retries**;
after victory, its ordinary cost is 4 MP in every area.

The lesson requires conscious active Caelan and his equipped blade, without a
minimum MP requirement or automatic resource refill. The pending formation can
be deferred for preparation and resumed from its cave position. Failure or
withdrawal does not unlearn an already successful discovery. Victory and its
once-only rewards clear the lesson and release normal weighted selection;
the miniboss cannot bypass it. Resonance, skill ownership and battle clearance
are separate saved facts. Older journeys with prior cave encounters preserve
their progress and receive Aqua Edge without replaying completed content. See
[Caelan’s opening progression](CAELAN_AQUA_PROGRESSION.md).

## Encounter roster

Outer covers the entrance and Vein Gallery. Middle covers the grotto, Upper
Passage, Splitstone Hollow and Keeper's Recess. Deep covers Deep Passage and
Deep Gallery. Room polygons and explicit route bands select these pools;
the configuration validates coverage rather than guessing through walls.

| Formation | Outer | Middle | Deep |
| --- | ---: | ---: | ---: |
| Cave Bat | 15% | 5% | 3% |
| Lithrusk | 10% | 5% | 3% |
| Veylume | 0% | 10% | 7% |
| 2 Cave Bats | 25% | 10% | 7% |
| Cave Bat + Lithrusk | 25% | 15% | 10% |
| Cave Bat + Veylume | 15% | 20% | 18% |
| Lithrusk + Veylume | 0% | 10% | 15% |
| 3 Cave Bats | 10% | 5% | 5% |
| 2 Cave Bats + Lithrusk | 0% | 5% | 5% |
| 2 Cave Bats + Veylume | 0% | 8% | 10% |
| Cave Bat + Lithrusk + Veylume | 0% | 7% | 10% |
| 4 Cave Bats | 0% | 0% | 2% |
| 3 Cave Bats + Lithrusk | 0% | 0% | 1% |
| 3 Cave Bats + Veylume | 0% | 0% | 4% |

Columns total 100%. The deeper pool gives 13% singles, 50% pairs, 30% trios
and 7% quartets. Veylumes appear in 15% of outer encounters, 55% of middle
encounters and 64% of deep encounters. A formation contains at most one Lithrusk and one Veylume.
All three species roll levels 2–3 in the outer cave, 3–4 in the middle, and
4–5 in the deep cave, independently and uniformly per enemy. The introductory
battle remains two level-2 Cave Bats. Encounter spacing remains 16–36 tiles
with a mean and mode of 26 tiles.

Pending encounters from earlier saves retain their already-selected levels;
new encounters use the revised pools after settlement.

Party defeat uses [Game Over and save loading](SAVE_SYSTEM.md), preserving
manual slots and autosave history. Victory and successful escape request a
recovery autosave after their transactions settle.

## Entry, combat and return

Entry briefly focuses the real exploration frame on the party, then presents
an actual loading screen. Only after that screen has been drawn does the
controller construct combatants, load sprite banks and prepare the selected
battlefield. A short reveal opens combat. Escape/focus loss pauses entry and
held inputs cannot carry through to spend a combat turn. Loading or checkpoint
failures offer retry while retaining the same ticket.

Four random-encounter native asset-pack battlefields represent the outer galleries, Reflecting
Grotto, Splitstone Hollow and Deep Gallery. Each has 24 frames over a six-second
cycle, pulsing wall microcrystals and a static reduced-motion frame. The grotto
adds water and drips. A cached renderer frames the scenery for the visible
combat floor at different UI sizes.

`BattleModel.from_bestiary_group` supports one to four independent enemies.
Each living party member, enemy and active bot receives an independent uniform
0–50% starting ATB roll for normal battles. Opening enemy target cycles are
spread across living party members. The scripted first-weapon and cave Aqua
lessons retain their authored opening opportunities. Each enemy owns its HP,
MP, action sequence and charge
target; victory requires defeating all enemies.

For groups, Attack and offensive skills open target selection. Arrow keys and
Enter select/confirm a living foe, and Escape returns to commands. A white
finger points down at the selected enemy, with a static red circle beneath its
sprite. Hovering a living enemy selects it without spending a turn; clicking
its sprite or status card immediately executes the highlighted attack or
offensive skill, including before a separate target confirmation. Support
skills retain their normal menu behavior. Unavailable skills explain their
requirements without spending MP or ATB. Cards show distinct names, HP and ATB; duplicate Bats
receive distinguishing labels. Bots and attacks retarget defeated enemies.
The single-enemy controls remain available for existing encounters.

Compact large-text layouts arrange three or four enemy status cards in one
row, keeping every HP/ATB bar visible and reserving space for the finger above
the sprites. The selected enemy's full name appears in the top announcement box
when no ability, event or incoming-attack warning is being shown.

Incoming prepared attacks identify the charging
enemy, attack name and living target. Warnings persist across other actors'
turns and rotate when several enemies are charging; queued routine status
notices yield to these warnings. Longer announcements page their full text
inside the same fixed-height box, including at 150% text size.

Tusker preparation and Veylume's Gather Charge produce a red lightning-flame
power aura, held through player decisions and the attack's release until
impact. Each enemy's preparation state controls its own aura. KO, canceled
preparations, unaffordable follow-ups and battle results clear the warning.
Effects follow the scene clock, pause with the battle, stay within the field,
and use a static frame under Reduced Motion. The aura does not change elemental
affinities, damage, action timing or ATB. Authored battle scripts can present an
emote with `BattleScene.announce(text, actor=...)`; presentation never mutates
combat state. See [review captures](reviews/mira_rig_continuity/README.md).

Victory resources and reward receipts are checkpointed before returning to
the exact cave position. EXP from every defeated monster is summed, then each
living active combatant receives that full amount. KO combatants, reserves and
bots receive no EXP; fleeing or defeat grants none. Eligibility uses actual
end-of-battle HP. EXP, stat growth and item drops share the same once-only award
and checkpoint. Continue can resume pending or already-awarded Spoils without
repeating grants. Cave victories preserve KO party members; level-ups increase
maxima without restoring current HP/MP. Failed return checkpoints roll back the
counter/resources so retry cannot consume another random roll. Fleeing preserves
spent resources.
The pending MQ03 outing, escorts and treasures remain intact, including through
cave victory and spoils. First cave entry permanently releases the MQ03
emergency music override; later outdoor visits use normal area music. This
music handoff does not advance the quest stage.

Cave exploration loops **Elden Vale Sanctuary Cave**. Battle entry temporarily
switches the soundtrack to **Kindled Courage**. Victory, fleeing and defeat fade
the cave track back in at its interrupted playback position; results and Spoils
keep that resumed stream. Loading a pending battle first selects the cave cue
so returning from it cannot accidentally resume the title theme.

Enemy stats, XP curves, base damage formulas and item-drop definitions remain
unchanged. Aqua Edge’s magical component now applies the stored Water response
and matching-element absorption; its physical component remains ordinary.
Group EXP now feeds saved character levels and deterministic
growth. Spoils shows each character's animated EXP bar, zero-EXP KO state or
maximum-level state, followed by acknowledged level-up sheets when needed. A
sheet uses black old values, green arrows and green new values with numeric
gains on light parchment. Quiet EXP and level-up effects honor Effects volume
without replacing the resumed soundtrack. Party and Characters menus expose
levels and progress; see [Leveling](LEVELING.md) for save compatibility and rules.
The three normal cave species currently have pending item drops, so their resolved
drop bundles include independent Potion, Revival Salts, Ether and Rest Kit rolls for every enemy. See [Consumables](CONSUMABLES.md). Stagger, techniques beyond the three learned elemental Edges, and
post-miniboss story resolution remain
separate work. The one-time level-seven Vespermaw encounter is live in the Echo
Chamber after the introductory lesson clears. Optional level-five Embravyr and
Nivareth use their own protected chambers, tickets and receipts; they are never
selected by a weighted pool. Their guaranteed Red/White focuses and learned
Edges do not change random formation weights or the 16–36-tile countdown.
See [elemental cave encounters](ELEMENTAL_CAVE_ENCOUNTERS.md).

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
