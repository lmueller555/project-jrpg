# Mira Bolt Shot firing repair

Retained complete generated masters for the basic .80 s action. `firing_initial_authored.png` is the first eight-pose master; `firing_authored.png` is the targeted forearm latch/plate correction. Both are unmodified image-generation outputs. The source prompt is in `generation.json`.

The export uses a single uniform nearest-neighbor scale, 45/448, at native position [4,10]. The approved attack_03 snapshot protects y<26 (head identity) and y>=36 (waist/hips, both leg chains and boots). Only the authored full drawing's y26..35 repair region replaces the forearm/upper-arm/shoulder performance. No limb is stretched, translated independently, rotated, or procedurally generated. `recipe.json` records source hashes, exact restoration windows and unaffected-output hashes. The accepted first three aim drawings remain pixel-identical. Their initial 240 ms are followed by 40 ms of latch/plate compression.

## Native timeline

0–100/100–180/180–240 ms: existing lift and aim.
240–280: latch compression, supported cuff.
280–320: plate snap and tiny attached brass wedge.
320–370: articulated elbow recoil.
370–430: shoulder/elbow recoil peak.
430–500: settle.
500–580: small cuff/strap follow-through.
580–680: lower.
680–800: rest.

Release stays exactly 280 ms, impact stays exactly 400 ms, complete action stays 800 ms. No model, damage, resources, ATB, other skill, world or cinematic file changes. Source cells82–89 append to the original82 sheet cells. The original unreferenced attack drawings remain as historical sheet cells.

## PR2 release contract

`MiraCombatArt.shot(elapsed, impact_at, floor_point, target_point, resolved=False)` remains compatible. `origin` is sampled from `world_anchor('attack', 280, 'muzzle', floor_point)` and freezes for the whole flight. `muzzle` follows the current cuff. The snap frame's exact canvas-local lens center is **[14,28]**, with fixed floor **[32,54]**. At existing2x battle scale, origin is `floor_point + (-36,-52)`. No projectile exists before .28 or at/after .40. The 40 ms wedge is attached to the snap frame, omitted in Reduced Motion; the core drawings, clack and projectile remain.

Rebuild: `python tools/build_mira_combat.py` (base bank then scoped firing export).
Review: `python tools/capture_mira_bolt_firing.py`.

This is implementation evidence, not an assertion of user visual approval. Independent QA precedes merge.

The generated atlas is 1774×887. Uniform 448-pixel extraction windows retain the
chosen authored crop/registration, with transparent outer-edge padding. Manifest
`source_bounds` clamp to the real atlas pixels; runtime RGBA exports do not change
when reporting those honest provenance bounds.
