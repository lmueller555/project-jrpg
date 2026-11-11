# Mira wearable arm rig: retained source artwork

This is the phase-one art source for Mira's external, wearable arm augmentation.
Her arm is intact inside the leather straps, graphite supports and brass cuff.
The source drawings retain her pink work shirt, flower, ponytail, trousers and
boots. They replace the handheld combat launcher with a forearm emitter.

Both transparent PNGs are retained exactly as returned by `image_gen.imagegen`.
`generation.json` records their checksums, references, source grids and prompt
summaries. Exporters perform alpha isolation, shared palette reduction,
nearest-neighbor sampling and registration; they do not draw or warp anatomy.

## Drawing inventory

`base_authored.png` contains 42 drawings in a six-column/seven-row atlas:
four idle, eight basic attack, two guard entry, two held guard, four guard impact,
four hurt, six rig activation, four victory, four defeat and four walk drawings.
Their state ordering and current action timing remain compatible with the
existing combat renderer. The `rig_activation` state depicts operation of the worn cuff controls.

`skills_authored.png` contains 40 additional drawings, eight columns/five rows:

1. Charged Bolt: lift, brace, aim, charge, release, recoil and recovery.
2. Bulwark: forearm rise, unfolding projector plates, open-hand hold and closure.
3. Repair Pulse: unlatch, extend engineering nozzle, aim, activate and retract.
4. Impact Bolt: planted attack, recoil into protective stance and recovery.
5. Arc Discharge: conductor deployment, supported aim, electrical release and closure.

Each row is a complete eight-frame sequence. These five sequences are art-only
previews in phase one; their gameplay abilities are not registered or usable yet.

## Registration and reproducible exports

Run from the repository root:

```sh
python tools/register_mira_arm_rig.py
python tools/build_mira_combat.py
```

`registration.json` records every source cell, atlas-relative source rectangle,
cell-relative projected floor, lens, controller, tool and projector attachment.
Base poses retain their previous measured boot-center X positions; floor Y is
remeasured against the new art. New skill poses use the midpoint of the two boot
contact regions. No character uses a silhouette centroid for floor placement.

All 82 drawings use the **same fixed 0.225 source scale**. Crouched or kneeling
poses remain shorter; they are not stretched to standing height. Runtime frames
use a 64×64 transparent canvas and anatomical floor `[32,54]`. All share one
96-color palette. The emitted manifest includes each atlas checksum, each
frame's source provenance and attachments, animation durations and contact marks.
`spritesheet.png` contains the 82 native frames in an eight-column layout.

Existing `world_*` assets and narrative sprites are intentionally untouched in
this visual phase. Story continuity and bot removal belong to the later phases.
