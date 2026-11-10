# Elemental cave encounter review

Historical capture: EXP values predate the `24 × level^0.4` reward curve.
See [current leveling rules](../../LEVELING.md) for live values.

These captures show the production continuous cave, optional Embravyr/Nivareth
encounters, full combat cycles, guaranteed focus rewards and acknowledged gem
installation. The creatures are pure elemental Aether formations with their
own authored art banks.

- [All actual-game captures](contact_sheet.png)
- [Embervein Chamber](embravyr_room.png) and [Stillfrost Chamber](nivareth_room.png)
- [Continuous cave map](continuous_cave_map.png)
- [Fire charge warning and aura](embravyr_charge_warning.png)
- [Fire exhaustion: +50% damage](embravyr_cooling.png) and [Ice exhaustion](nivareth_settling.png)
- [Aqua Edge at 0 MP](embravyr_edge_0mp.png) and [Flame Edge at 0 MP](nivareth_edge_0mp.png)
- [Red focus installation](embravyr_focus_installation.png) and [White focus installation](nivareth_focus_installation.png)
- [Red installation at 150% text](embravyr_focus_installation_150.png) and [White at 150%](nivareth_focus_installation_150.png)
- [Detailed verification and source hashes](verification.json)

Both recorded fights are played to actual victory with menu, mouse and keyboard
input. Every enemy action is observed, including its preparation, heavy hit and
recovery. Caelan begins with 0 MP and remains at 0 while using the encounter's
free elemental Edge. The party carries its actual remaining HP/MP and earned
EXP into the second fight. The first victory installs Red and learns Flame
Edge; the second uses it against Nivareth, then installs White and learns Ice
Edge. No enemy HP, action clocks or battle outcomes are edited for these images.

The explicit fixture initializes older quest work and the already-completed
Aqua lesson, then plays MQ03 departure and Sanctuary arrival through production
dialogue and travel. Public progression APIs establish the actual Caelan/Mira
party at level four with rested resources; Caelan's MP is then set to zero.
Near-room placement and fixed encounter seed 0 shorten setup. These are review
fixtures, not automatic party recruitment, healing or level grants in the game.
Text size briefly changes to 150% for labelled installation captures.

The independent actual-Game suite also covers both completion orders, partial
completion, entry/Spoils/acquisition Continue, KO Caelan, defeat and retry,
Flee, failed saves and atomic reward rollback. Those persistence tests may
explicitly finish a battle to isolate settlement; the screenshots above use
complete real fights instead. See [the encounter guide](../../ELEMENTAL_CAVE_ENCOUNTERS.md)
for final rules and data.

## Full authored animation banks

The runtime sheets contain every registered pose. Their manifests retain the
source drawings, extraction rectangles, timing and original sheet hashes.
No generated intermediate or transformed copy is counted as another authored
pose.

| State | Embravyr frames | Nivareth frames |
| --- | ---: | ---: |
| Emergence | 16 | 8 |
| Idle | 16 | 16 |
| Basic attack | 16 | 16 |
| Party-wide spell | 24 | 24 |
| Gathering | 24 | 24 |
| Charged hold | 16 | 16 |
| Heavy attack | 24 | 24 |
| Recovery | 16 | 16 |
| Hurt | 8 | 8 |
| Defeat | 24 | 24 |
| **Total** | **184** | **176** |

- Embravyr: [full runtime sheet](../../../assets/combat/embravyr/spritesheet.png), [manifest](../../../assets/combat/embravyr/animation.json), [source drawings](../../../assets/source/combat/embravyr), [dedicated art review](../embravyr_combat/README.md).
- Nivareth: [full runtime sheet](../../../assets/combat/nivareth/spritesheet.png), [manifest](../../../assets/combat/nivareth/animation.json), [source drawings](../../../assets/source/combat/nivareth), [dedicated art review](../nivareth_combat/README.md).

## Reproduction

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  python tools/capture_elemental_cave_encounters.py
python tools/capture_elemental_cave_encounters.py --check
```

The capture tool uses disposable save and settings directories. It writes PNGs,
a contact sheet and metadata, without a walkthrough video. `--check` validates
captured source/artifact hashes and evidence of both real victories, all five
actions, zero MP and the ×1.50 exhaustion window. Captures become historical
if those source hashes change; rerun the capture before calling them current.
