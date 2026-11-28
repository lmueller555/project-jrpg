# Lucan: bridge-ascent whole-figure performance

The selected runtime contract is
`assets/story/fire_veinhold_opening/shot08/characters/lucan/actorperformance.json`.
It declares 133 chronological camera-transition samples and 48 overhead run poses,
with a SHA256 for every used PNG. The physical run clock is 800 ms for two steps,
right contact at 0 and left contact at 24, while the camera/scene samples at 60 Hz.
Lucan retains his approved bare head, short dark hair, polished steel armor,
oxblood cloth/gold edging, right-hand sword and left-arm kite shield.

## Source and registration

Every new final figure comes from one complete ImageGen drawing. Raw masters,
exact prompts, generation IDs and reference hashes remain in generation-record
JSON files, including rejected trials. Alpha floor 16, complete-cell cropping,
one uniform whole-image scale, and whole-image registration are the only export
operations. No separated limb assembly, anatomical pixel replacement, body
warping or figure crossfade produces final art.

The default artwork canvas is 1024×1536 at 500 art pixels/metre, ground anchor [512,960].
Early samples 0–15 directly reuse their approved 768×1024 PNGs with anchor [384,960];
keeping their original canvas also preserves the exact prior-shot seam. Subsequent
large figures use actual camera-specific drawings; distant matching-phase reuse
of the overhead cycle is recorded explicitly by the performance profile.

`early_registration.json` and `bank_registration.json` retain exact selected
whole-image recipes and output hashes. Other registration files and generation
records retain authoring/review history; matching selected output hashes determine
which recipe is current. Rigid cranium/pauldron dimensions establish density.
Occupied figure height and changing face/eye-template size do not establish scale.
A naturally foreshortened overhead figure remains physically the same adult.

The Blender guide files are reference-only pose/camera studies, never final art
or canonical character geometry. In particular, `close_recovery_v2` reconstructs
a plausible connected 35→48 recovery from approved 35 and calibrates the adult
cranium center, replacing a generic oversized mannequin head. Its finite
same-phase redraws preserve the successfully reviewed leg ownership while
correcting the camera view and upper-body carry. `overhead_motion_repair`
records the bounded passing-knee/calf occlusion repairs and loop-seam repair.

## Validation

Rebuild selected exports and run the provenance audit after the selection is stable.
The bank authoring entry point also delegates to this exact selected-recipe rebuild
once `selected_performance.json` exists:

```sh
python assets/source/cinematics/fire_veinhold/bridge_ascent/characters/lucan/rebuild_selected.py
python assets/source/cinematics/fire_veinhold/bridge_ascent/characters/lucan/check_source_provenance.py
python assets/source/cinematics/fire_veinhold/bridge_ascent/characters/lucan/check_source_provenance.py --check
```

It verifies retained raw/reference hashes and reproduces every selected RGBA
export from its one-master recipe. This establishes lineage and reproducibility,
not motion quality. Actual-camera native controls, complete chronological/baked
scene review and final acceptance are recorded separately in
`docs/reviews/veinhold_bridge_ascent/` so review updates do not alter source hashes.
