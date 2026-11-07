# Progression cleanup review

Production captures show the eight-option Pause menu, the Characters screen
with attributes, and item-only Spoils of Battle. Each screen is captured at
960×640 with normal text and at the minimum 480×320 window with 150% text.

| Screen | Normal window | Minimum window, 150% text |
| --- | --- | --- |
| Pause | [960×640](pause_960.png) | [480×320](pause_480_text_150.png) |
| Characters | [960×640](characters_960.png) | [480×320](characters_480_text_150.png) |
| Spoils | [960×640](spoils_960.png) | [480×320](spoils_480_text_150.png) |

The capture uses a real isolated `Game` with temporary journey and settings
files. Opening guidance is disabled for review and Caelan is positioned near
the actual test Bat. Keyboard input opens the menus; ordinary attacks defeat
the Bat with normal starting stats and RNG seed 7. The production victory flow
awards one Aether Emerald and records its once-only receipt. Waiting, saving,
continuing the journey and leaving Spoils preserve that one grant. No XP is
awarded, and natural attributes remain unchanged.

The renderer records no retired progression labels on these screens. No poses,
HP values, damage calculations, item rewards or rendering calls are replaced.
The screenshots use the actual rendered game frames.

Reproduce from the repository root:

```sh
python tools/capture_progression_cleanup.py
python tools/capture_progression_cleanup.py --check
```

`verification.json` records the production-source and artifact hashes, rendered
labels, window/text settings and real victory/Continue checks. The checker
rejects stale sources or modified captures.

Independent real-Continue coverage in
[`test_progression_cleanup.py`](../../../tests/test_progression_cleanup.py)
also loads a genuine paid-reward save fixture: 100 earned maximum HP, current
HP/MP 220/7, learned Aether Dart and an existing reward receipt. Title inspection
leaves the original bytes intact. Successful Continue preserves the effective
240 maximum HP, resources, skill, inventory, quests and receipt; subsequent
Continue does not apply growth again.

## Regression results

The focused removal suite passed **704 tests and 2,095 subtests across 69
modules**. A final frozen-file compatibility follow-up passed **17 tests and
57 subtests**, covering the late malformed-save recursion guard. Pending and
already-awarded victory checkpoints both retain their paid stats, learned
abilities and once-only item receipt across real Continue.

All **216 current test modules** were covered across the focused run and three
parallel batches. Those batches reported **2,191 passes and 8,255 passing
subtests**, with **16 pre-existing failures/subtest failures**. Every failure
was reproduced on unchanged main at `345d1a65`; no new regressions were found.
The failures concern existing narrative expectations, protected art manifests,
room counts, a historical quest fixture and sparse map/dialogue test stubs.

See [the validation record](validation.json), [focused test output](impacted_tests.txt),
[final compatibility checks](compatibility_followup_tests.txt), and
[baseline failure proof](baseline_failures.txt). The baseline
[reproduction record](baseline_failures.json) contains the exact test nodes and
command; its four parameterized crossroads failures belong to one parent test.

The same test module also resumes genuine legacy-format pending and already
awarded Spoils records. Paid HP and learned skills survive; pending items are
granted once, and already awarded items are retained without another grant.
Its final focused run passed **3 tests and 2 subtests**.
