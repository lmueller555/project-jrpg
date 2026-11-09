# Caelan’s Blue gem and Aqua Edge

Caelan receives one Blue Water gem in Mira’s Blade, accidentally discovers
Aether Edge at the millrace, then learns Aqua Edge at the Sanctuary confluence.
Optional level-four Embravyr and Nivareth encounters then add Red/Fire and
White/Ice focuses with Flame Edge and Ice Edge, in either order. Their
[encounter guide](ELEMENTAL_CAVE_ENCOUNTERS.md) records the implemented rewards
and combat rules; additional gears remain future work.

## Playable sequence

1. The MQ02 gift owns and equips the blade with **Blue only**. Its other
   sockets are empty in the gift, selector and equipped sword presentation.
   Unowned sockets cannot be selected. The gift does not teach a combat Edge.
2. The Boar opening teaches Guard against its visible charge. Skills offers
   only Aqua Edge. That Water attempt sputters for 0 MP, then inadvertently
   follows through as **Aether Edge**, without a second menu selection. The
   successful strike costs 4 MP and learns Aether Edge at impact.
3. On entering the Sanctuary cave with the blade, Caelan notices stronger
   ambient aether. The Blue gem glows, and he wonders if he can focus Aqua Edge
   here. This short, acknowledged scene is saved independently of the skill.
4. The existing **16–36-tile** encounter countdown selects **two level-two Cave
   Bats** for the first fight. The player chooses Skills → Aqua Edge and a foe.
   Enemy, Mira and Rivet actions wait until that first successful cast. It
   teaches Aqua Edge at impact, then ordinary ATB combat resumes.
5. Aqua Edge costs **0 MP throughout this introductory encounter and all its
   retries**, including after the discovery is already known. Victory and its
   ordinary rewards clear the introduction. Later encounters use its normal
   **4-MP** cost, in the cave and elsewhere. The two later optional elemental
   teaching encounters waive all learned elemental Edge costs throughout their
   fights and retries; ordinary battles and Vespermaw retain 4 MP.
6. Embravyr's Aether settles into a Red focus and Nivareth's into a White focus.
   Each guaranteed victory award installs its gem and learns the corresponding
   Edge. First and second acquisition dialogue adapts to either order, and
   waits for a KO Caelan to recover without withholding his earned focus.

The confluence creates an opportunity to discover the skill; it does not become
a permanent location requirement. Aether Edge remains learned and usable.
The isolated water spell during MQ02 remains a world action and does not teach
Aqua Edge early. Aether Sapphire, Ruby and other inventory materials do not
install focus gems.

## Combat data

| Technique | Physical potency | Magical potency | Magical element | MP |
| --- | ---: | ---: | --- | ---: |
| Aether Edge | 1 | 0.5 | Non-Elemental | 4 |
| Aqua Edge | 1 | 0.5 | Water | 0 in introductory encounter; normally 4 |
| Flame Edge | 1 | 0.5 | Fire | Normally 4 |
| Ice Edge | 1 | 0.5 | Ice | Normally 4 |

All learned elemental Edges cost 0 MP in the two optional elemental teaching
encounters. Aether Edge remains 4 MP there.

Each elemental Edge’s magical component applies the target’s authored matching
elemental percentage or matching-element absorption. Its physical component remains an
ordinary physical strike. The resolver accepts every stored percentage from
0 through 200, including intermediate weaknesses and resistances. Absorption
uses the neutral-affinity magical amount, restores at most missing HP and does
not revive a defeated enemy. The approved base formula and damage cap remain.
Elemental responses are not automatically displayed in the combat UI.

## Ownership and checkpoints

`character_abilities.py` stores gem ownership separately from `gear_focus`,
first-weapon history and learned abilities. Owning a gem does not teach its
skill. Acquiring the blade owns Water; selecting a focus must reference an
owned gem. The gift, accidental Aether discovery and Aqua discovery therefore
cannot substitute for one another.

`cave_lesson.py` owns three boolean story facts alongside its schema version:
`resonance_seen`, `battle_cleared` and `deferred`. Permanent Aqua knowledge stays
in the character ability owner. The random encounter ticket identifies the
lesson with `lesson: "aqua_edge"`, and fixes the pair, levels, combat seed,
battlefield, receipt and return position before combat loads.

A successful discovery checkpoints its learned skill and current party
resources together. A failed write rolls both back and retries the checkpoint;
quitting cannot keep the skill while refunding the cast. Victory clears the
lesson in the same once-only transaction as its receipt, EXP, resources and
ordinary item bundle. Spoils can resume without replaying grants.

Defeat or withdrawal keeps the exact introductory ticket and any already-earned
Aqua knowledge. A deferred retry lets the player prepare or travel instead of
immediately restarting combat. Returning to the saved encounter position offers
an explicit retry. Caelan must be conscious and active with the blade equipped;
there is no MP minimum, hidden refill or required healing detour. An already
learned retry skips the discovery instruction while retaining the 0-MP cost.
The introductory fight takes priority over the miniboss. After victory, the
existing weighted cave roster resumes.

## Existing journeys

Saves without the gem-ownership extension migrate to Blue only, retain earned
Aether Edge and preserve XP, attributes, inventory, quests and rewards. Completed
MQ02 gift scenes are not replayed. Saves that already encountered cave enemies
or entered the boss migrate without a surprise forced introductory battle;
their existing tickets, Spoils transactions and boss ownership remain intact.
A completed legacy-bypass MQ02 journey that still lacks the blade receives one
Blue-only blade and the starter Aether Edge idempotently. This keeps the older
weaponless route playable under the current progression without replaying the
gift or changing HP/MP. Earlier active legacy routes keep compatibility dialogue
until their completed outing can migrate.

## Verification

Focused tests cover the actual gift/Boar route, one automatic Aether discovery,
zero-MP cave entry and repeated lesson casts, elemental response, owned-gem
selection, save/Continue boundaries, failed writes, defeat/withdrawal and
normal encounters after victory. See the relevant suites under `tests/` and
[the encounter rules](CAVE_RANDOM_ENCOUNTERS.md).

The [current visual review](reviews/caelan_aqua_progression/README.md) shows the
gift, both Boar effects and the cave lesson using actual game input and rendering.

Earlier [four-focus gear](reviews/caelan_gear/README.md) and
[two-attempt MQ02](reviews/mq02_spellblade/README.md) captures are historical
records of those implementations, rather than previews of this sequence.
