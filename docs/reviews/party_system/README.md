# Party system review

These are production game frames captured from a disposable fresh journey. The
review fixture explicitly recruits Mira, Lucan, Rhea and Edran through the public
story API, makes Rhea unavailable with a reason, and supplies visibly depleted
resources, including KO Lucan. Those future recruitments are capture fixtures;
they do not add recruitment events, skills, equipment or progression to the game.

- [Menu animation, native 960 × 640](party_menu.gif)
- [Silent video, 960 × 640](party_system_silent.mp4): draft/cancel, mouse selection,
  a saved and reloaded event gate, a locked formation, town followers and actual
  commands for all three combatants.
- [Normal party menu](roster_normal.png)
- [Unavailable companion and reason](roster_unavailable.png)
- [Minimum 480 × 320 window at 150% text](roster_minimum_150.png)
- [Scrolled reason at the same minimum size](roster_minimum_reason_end.png)
- [Unconfirmed draft](draft_before_cancel.png)
- [Selection gate](selection_gate.png) and [the same gate after reload](selection_after_reload.png)
- [Confirmed event lock](event_locked.png)
- [Three-member combat](three_member_battle.png) and [Mira's live action](mira_three_member_action.png)
- [Three-member combat at minimum size and 150% text](three_member_battle_minimum_150.png)
- [Exploration trail](travel_trail.png)

The cancel and confirmed-switch checks preserve every character's HP/MP, including
the KO reserve. Before the combat reel, the fixture explicitly restores Lucan to
97 HP and selects Caelan/Mira/Lucan. This is recorded in the evidence rather than
attributed to switching. The encounter then uses production contact entry,
transition, ATB, input, actions, animations and rendering. No battle clocks,
gauges, damage results or action frames are assigned by the capture. The reel
ends before settlement, leaving progression unchanged. Pillow only encodes the
already rendered menu frames into the GIF; FFmpeg encodes the actual window.

Reproduce with the project's Python environment and FFmpeg installed:

```sh
python tools/capture_party_system.py
python tools/capture_party_system.py --check
```

Saves and settings are confined to a temporary directory. `verification.json`
records inputs, video stages, screenshots, assertions and artifact hashes.
`fingerprints.json` records the relevant production code and character assets.
`--check` checks those hashes, confirms the video has no audio stream, and checks
that the three actors received real commands. Any source change requires a new
capture before considering that evidence current.

## Existing MQ02 continuity

[Full MQ02 capture](mq02/mq02_gear_combat_silent.mp4) · [Victory](mq02/victory.png) · [Awarded Spoils](mq02/spoils.png) · [Evidence](mq02/verification.json)

The existing production driver also completes 90.97 seconds through the weapon
gift, Guard lesson, failed matching elemental attempt, Aether Edge discovery,
Overclock, three Bolt Shots, victory and settled Spoils. Mira remains a required
temporary party member during the outing and retains the battle's 253 HP / 25 MP
after settlement. The driver uses temporary files and its existing prior-quest,
station and RNG fixtures; it does not override combat resources or clocks.
The auxiliary four-gem reel is omitted. Source hashes remain unchanged during
the capture.

## Validation

All **622 regression tests and 934 subtests pass** across 58 selected modules.
One unchanged crossroads manifest assertion is excluded after reproducing it on
main; it expects a cast without the already-added Lucan. An additional final
24 UI/gameplay checks pass, including the pre-confirmation lock explanation.
See [validation details](validation.json) and [regression output](tests.txt).

A broader, interrupted comparison also reproduces six existing failures on main
(doctrine text, historical protected-art hashes and an outdated room count).
The older character-save fixture now omits the party envelope it predates, and
the MQ02 test driver selects its requested gem through real keyboard input.
Production save validation stays strict and no story text or art is changed.
