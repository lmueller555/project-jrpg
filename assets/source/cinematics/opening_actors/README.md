# Opening cinematic — quiet character acting

These transparent source sheets were generated for the real-time opening
flashforward. They preserve the existing Caelan and Mira designs while adding
resting and conversational poses that are absent from their combat animations.

- `caelan_quiet_generated.png`: seated rest, cup in lap, glance, sip, outward
  glance and relaxed standing poses.
- `caelan_inbetweens_generated.png`: empty-handed reach, cup receipt,
  withdrawal, lifting the cup and two stages of rising.
- `caelan_drinking_generated.png`: registered lift, sip and lowering frames
  authored from the original seated-cup pose. This action keeps Caelan's bowed,
  forward/down three-quarter head bearing throughout. It supersedes the older
  drinking/lifting frames, whose different head bearings produced a sideways
  glance during the action. The original source sheets remain preserved.
- `mira_quiet_generated.png`: kneeling rest, cup offer, seated rest, glance,
  standing and a supported rising/lowering pose. Mira's gathered short ponytail
  and cream flower were checked against her approved overworld design.
- `mira_inbetweens_generated.png`: lifting the cup, releasing it, lowering empty
  hands, rising from a kneel and two stages of lowering onto a seat.

The source sheets remain intact. Rebuild the native PNGs and manifests with:

```sh
python tools/build_opening_cinematic_actors.py
```

To update only the drinking action while leaving every other Caelan frame and
all Mira exports untouched:

```sh
python tools/build_opening_cinematic_actors.py --drinking-only
```

The exporter needs Pillow and NumPy. It finds the six separated opaque actors
in each sheet, removes the semitransparent generation haze, crops them and
uses one common physical scale per source sheet. The two source sheets for an
actor have different source-pixel densities; their scale factors account for
that difference. It does not lengthen arms, bend fixed legs, stretch individual
poses or synthesize anatomy. Every exported frame has a 96×112 canvas and a
48×104 floor anchor. Source bounds, hashes and scale factors are recorded in
each runtime `animation.json`.

The 28 authored frames include explicit transitions for the handoff, drinking
and Mira's kneeling/seated/standing changes. Both characters share the same
ground plane. With scene anchors at x=670 and x=725, Caelan's receiving hands
meet Mira's offering hands near x=695; the cup then moves back into his lap.
The seat surface is approximately 18 pixels above their planted-foot baseline.
No chair or bench is baked into the actor frames.

The exporter also creates development-only contact and registration previews
under `work/`; those are not runtime dependencies.

The corrected drinking action has three 160 ms lifting frames, the held sip
pose, and three 160 ms lowering frames. Cup contact with the mouth is authored
in the source artwork. The original seated-cup pose, receiving action, other
Caelan acting and every Mira pose are unchanged. The source export uses a
single `.134` scale across all six drinking drawings, matching the existing
64-pixel seated body height and `[48, 104]` floor anchor. Review files are
`work/cinematic-drinking-contact.png` and `work/cinematic-drinking-preview.gif`.
