# Vespermaw live encounter review

The optional elemental-chamber update changes Vespermaw's exhaustion from +25%
to **+50% incoming damage**. This retained capture is historical evidence of
the earlier encounter build. The current [elemental encounter review](../elemental_cave_encounters/README.md)
shows the shared +50% recovery rule, while [the Bestiary](../../BESTIARY.md#vespermaw)
records Vespermaw's current data.

These retained captures show the PR #162 build before Blue-only gem ownership
and the cave Aqua Edge lesson. Their original production hashes remain in
`verification.json`; the current capture tool seeds the earlier Aqua discovery
explicitly when reproducing this boss-only review. Current gem and lesson
visuals are covered by the [Aqua progression review](../caelan_aqua_progression/README.md).

[Encounter contact sheet](contact_sheet.png) · [Opening offer](approach_offer.png)
· [Roar](confluence_roar.png) · [Pounce warning](gather_resonance.png)
· [Recovery opening](exhausted.png) · [Spoils](spoils.png)
· [Defeat choice](defeat_choice.png) · [Safe return](defeat_quiet_shelf.png)

These captures use the production `Game`, actual Echo Chamber interaction,
introduction/loading, live Vespermaw battle rules, dedicated battlefield and
standard spoils flow. The earlier MQ01/MQ02 completion is a labelled fixture;
MQ03's meal, interruption, departure, Mira's return and Sanctuary journey use
the existing production input driver. The cave is entered through its real
Sanctuary approach interaction.

Natural level-seven attributes and full starting resources, a near-arena
position and combat seed 7 are review fixtures. No additional character is
recruited: the current outing's actual combat party is Caelan and Mira. Lucan's
story ownership remains unchanged. Combat uses Aether Edge, Overclock, ordinary
attacks and Guard when marked for Pounce. Enemy actions and damage are resolved
by the game; victory is earned through those commands.

The review observes all five steps of the combat cycle, gives each surviving
active character 1,110 EXP and collects one Aether Amethyst and one Aether
Sapphire. It verifies the saved defeated flag, cleared pending entry, valid
journey and unchanged MQ03, party event and resumed music.

A separate **low-HP fixture**, clearly labelled in its captures, starts the
same party at 1 HP and 0 MP. The live boss defeats them, then production input
chooses Retry and confirms that the original 1 HP / 0 MP are restored. After a
second actual defeat, Return to the Quiet Shelf exits safely with the boss
unbeaten and XP/inventory unchanged. This is not a full-heal or victory fixture.

No user save or settings outside a temporary directory is read or changed.
`verification.json` records production hashes, artifact hashes, action coverage,
EXP results and the defeat/retry checks.

Reproduce or verify from the repository root:

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python tools/capture_vespermaw_encounter.py
python tools/capture_vespermaw_encounter.py --check
```

Use `--output /tmp/vespermaw-live-review` for disposable alternative captures.
The retained art-only bank review remains separately available under
[`../vespermaw_combat/`](../vespermaw_combat/README.md).
That historical review records the earlier sprite rollout and its original
production hashes. Its source-match check flags the later live-combat changes;
this live encounter review verifies the current implementation.
