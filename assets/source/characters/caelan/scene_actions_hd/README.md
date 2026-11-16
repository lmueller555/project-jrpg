# Caelan HD scene actions

Active registry: `assets/characters/caelan/scene_actions.json`.
Export/check: `python tools/export_caelan_scene_actions_hd.py [--check]`.

These retained generated masters contain complete independent drawings based on
Caelan’s approved HD turnaround. The exporter only isolates connected hard alpha,
uniformly samples each declared sheet/pose family, translates whole drawings,
inks the one-artwork-pixel contour and composes separately owned props/FX.
It does not construct limbs, join upper/lower bodies, mirror asymmetric costumes,
rotate joints or synthesize pose interpolation. Runtime retains the native 2×
pixels while using the original logical canvases, ground anchors and cue clocks.

- `hold.png`: front/back/right empty carrying hands. Its incorrectly facing
  lower-left study is deliberately unused; `cast_wake.png` cell 4 supplies left.
- `crouch_give.png`: four directional crouches followed by four directional gives.
- `seated_eat.png`: front/right sitting, glance, sitting bend; four eating keys.
- `cup_pass.png`: courteous cup handover, reaching toward the table then recovering.
- `cup_work.png`: retained seated studies (unused), then four workshop keys.
- `cast_wake.png`: casting-ready, raise, release; remaining used left-hold study.
- `sleep_rescue.png`: closed-eye pillow head, wake sit-up, corrected rear overhead
  reach/lower (pouch on viewer-left), then four complete assistance drawings.
- `lift_back.png`: shallow knee bend and recovery toward the sack ahead of Caelan.
- `carry.png`: four complete carrying keys per direction, front/back/left/right.
- `approved_turnaround.png`: unchanged approved visual reference.

Physical scales in `SHEETS` preserve head/torso proportions; seated and crouched
poses do not fill the standing height. Export registration grounds complete
figures. World and artwork units are declared in the registry and scene manifests.
`inputs/` retains only necessary timing/manifests and extracted tool, lantern-frame
and energy layers; it contains no old Caelan body PNGs. Tomas/household props
remain independently retained in `assets/source/story/sanctuary_opening/`.

`retired.json` records intentional retirement of earlier scene body exports,
masters and builders. `protected_travel.json` protects all 141 approved travel
PNGs byte-for-byte. The distinct opening/late-game cinematic and combat banks
have separate projections/costumes and are retained, not obsolete overworld banks.
Global construction and interaction guidance remains in the two central standards;
this file records only this bank’s implementation facts and source mapping.
