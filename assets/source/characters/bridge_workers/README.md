# Bridge crew: authored body animations

The mason retains the approved `male_01` moss/tan appearance; the surveyor retains
`male_03` slate/brown. Their normal directional idle and walking sprites remain
read-only. New full-body action frames live in the `mason/` and `tender/` source
folders, with original generations, prompts, registration and review images.

`tools/build_bridge_workers.py` invokes `tools/build_bridge_mason.py` and
`tools/build_bridge_tender.py`, then registers both manifests and the unchanged
shared props. Each role also supports `--check`. Runtime uses those authored
sequences for directional stone/cup handling, measuring, work, handoff, seated
drinking and recovery. Frame metadata keeps props aligned with the painted hands
and defines appropriate depth. The former front-body arm/leg assembler and its
flat action exports are retired.

All body frames share a 40×44 canvas, foot anchor [20,38] and consistent standing
scale. Clip registration uses uniform whole-body scaling while preserving
within-sequence crouching and seated proportions. The finite three-stone batch,
optional tea dialogue, saved beats and blocked-path behavior remain intact.

The nine props are preserved byte-for-byte under `common/`. Their original
material/crop registration remains in `props_export.json`, and the earlier
`tools/build_bridge_props.py` preserves that derivation. Sources include the
regional bench/fence/rubble, sanctuary kettle/cup and workshop timber surface.
The body pass changes no prop dimensions, surrounding scenery or checkpoint.

```sh
python tools/build_bridge_workers.py
python tools/build_bridge_workers.py --check
```

The [region NPC review](../../../../docs/reviews/region_npcs/README.md) covers the
current bodies and routine motion. The earlier `docs/reviews/bridge_crew/` remains
the initial implementation record.
