# Mira Bolt Shot: flight and shoulder impact (PR2)

Code candidate: `19ed3f25fe06d1e09cf55ad55ec4d9ab59813bde`.
Base: merged PR1 #580, `a997adbdfb9605c417012a3be35044dc29482e2d`.
This is the second scoped change. PR1's firing drawings, muzzle registration,
40 ms brass wedge and mechanical clack are retained unchanged.

## Real MQ02 comparison

Every capture starts a temporary **New Game**, plays the opening and MQ02 with
production walking/dialogue/command input, completes Guard → failed Aqua →
automatic Aether discovery, and chooses Mira's ordinary Attack. No quest facts,
character attributes or unlocks are seeded. RNG 7 makes the A/B damage comparison
repeatable. Normal journeys, Continue and settings are untouched.

A uses the committed PR1 `BattleScene`; B uses this candidate. Other runtime
inputs/assets are shared, including PR1's Mira art. Added Tusker banks are unused
in A and do not change occupied bounds or scale. Each clip has 64 production
frames at 60 fps, through the completed dust decay. MP4 audio reconstructs only
observed action cues through the production decoder/envelope at unity effects
volume, without music. GIFs are silent; `slow` is half speed.

| Mode | A: merged PR1 | B: this change | B, half speed |
| --- | --- | --- | --- |
| Normal | [MP4](normal_A_bolt_shot.mp4) · [GIF](normal_A_bolt_shot.gif) · [exact-time sheet](normal_A_contact.png) | [MP4 with clack/thock](normal_B_bolt_shot.mp4) · [GIF](normal_B_bolt_shot.gif) · [exact-time sheet](normal_B_contact.png) | [GIF](normal_B_slow.gif) |
| Reduced Motion | [MP4](reduced_A_bolt_shot.mp4) · [GIF](reduced_A_bolt_shot.gif) · [exact-time sheet](reduced_A_contact.png) | [MP4 with clack/thock](reduced_B_bolt_shot.mp4) · [GIF](reduced_B_bolt_shot.gif) · [exact-time sheet](reduced_B_contact.png) | [GIF](reduced_B_slow.gif) |

[Comparison checks](comparison.json) and the four `*_verification.json` files
retain 26 exact-time samples, source hashes, observed Reduced Motion state,
complete lesson state, HP, release/impact cues, floor anchors and camera.
The numbered native [recoil sheet](recoil_numbered.png) shows all four starting
idle phases, with protected hooves/head on the shoulder-only first key.

## What to inspect

- A solid, outlined brass shaft with a pointed steel leading tip appears from
  the authored muzzle at **0.280 s**. A short moving smear sheds fragments that
  peel back and die; there is no static PNG burst or muzzle-to-target beam.
- The tip approaches Tusker's incoming near shoulder, native **(59, 33)** relative
  to floor **(48, 62)**. At **0.400 s** the projectile vanishes and the same
  event owns a 55 ms local glint, fast directional sparks, heavier arcing flecks,
  slower dust (gone by 0.880 s), and a low, dry 96 ms thock.
- Shoulder compression precedes head recoil by 55 ms, then settles. Every idle
  phase has its own registered bank, so a raised head does not snap down first.
  Feet stay planted. The camera stays at 1× with zero pan/shake.
- Reduced Motion keeps the physical bolt and a small contact cue, but removes
  the flight smear/fragments and impact flecks/dust. No timing is lengthened.
- Guarded and lethal hits retain their prior hurt/guard/defeat paths. Other
  species use their registered body geometry, not Tusker's size or offsets.

The 0.280 release, 0.400 authoritative damage, and 0.800 action duration are
unchanged. All A/B HP/resolution clocks match, including 245 → 228 HP here.
The model, damage backend, ATB, tutorials, action definitions and other skills
are unchanged.

## Validation

- **101 focused tests passed:** Bolt FX/anchors/event boundaries, pause/focus,
  reduced motion, guarded/lethal paths, four recoil phases, body geometry for
  all other species at compact/large-text layouts, existing battle/party/rig,
  cave and elemental scenes, audio and asset provenance.
- **23 gameplay tests passed:** `test_mill_battle_gameplay` and
  `test_mira_rig_gameplay`, including defeat/flee/Continue, first aid, once-only
  rewards, repairs and barriers.
- `python tools/build_mill_combat_assets.py` reproduced all combat outputs
  byte-for-byte, including PR1 Mira. `git diff --check` passed.
- Four actual MQ02 captures passed their assertions. Each A/B pair has identical
  damage/resolution clocks and Mira floor; B holds Tusker's floor at (119, 196)
  during recoil. Both live Reduced Motion captures verified the setting is true.
- Full discovery was attempted before rebasing, not claimed as a pass: it had
  legacy failures and was stopped after 948 test entries to avoid mixing bases.
  Examples reproduced using the pre-change renderer include the Aqua retry
  deferred flag and old hover-multiplier expectations. Unrelated map/UI/source
  expectation failures were not expanded into this task.

Reproduce the final focused set:

```sh
PYTHONPATH=tests python -m unittest test_bolt_shot_fx test_mira_combat_scene test_battle_action_audio test_battle_action_fx test_mill_combat_assets test_battle_scene test_party_battle_scene test_mira_rig_scene test_mira_rig_model test_cave_enemy_battle_scene test_elemental_battle_scene -v
PYTHONPATH=tests python -m unittest test_mill_battle_gameplay test_mira_rig_gameplay -v
```

Capture exact source PNGs plus the retained summaries (temporary journeys only):

```sh
python tools/capture_mira_bolt_impact.py --output work/bolt-impact/normal-A --baseline-ref a997adbd
python tools/capture_mira_bolt_impact.py --output work/bolt-impact/normal-B
python tools/capture_mira_bolt_impact.py --output work/bolt-impact/reduced-A --baseline-ref a997adbd --reduced-motion
python tools/capture_mira_bolt_impact.py --output work/bolt-impact/reduced-B --reduced-motion
```
