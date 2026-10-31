# Grain workers: authored body animations

The two grain workers retain the approved `male_02` rust/charcoal loader and
`male_03` slate/brown coworker appearances. Their ordinary four-direction idles
and walks remain read-only. The routine now uses image-authored full-body work
and carrying sequences, with profiles and rear views suited to each action.

Each role has a source folder containing original generations, exact prompts,
export registration and review images. The role exporters crop and uniformly
register those authored bodies on a 40×44 transparent canvas with foot anchor
[20,38]. Per-frame data records the sack attachment, palm contacts, timing and
front/back depth. `grain_farm.py` chooses the pose and synchronizes the separate
sack with that data. Stationary work uses planted feet and natural weight shifts;
blocked carrying holds a supported load until the path clears.

`pose_reference.png` is retained as the original prototype reference. The former
front-body arm assembler and its flat work-pose exports have been retired.
The new role manifests are the live runtime source of work animation.

The small sack and cloth are byte-identical to their earlier artwork. Canonical
copies live under `common/`, allowing the shared builder to restore and verify
them without changing their shape or palette.

```sh
python tools/build_grain_workers.py
python tools/build_grain_workers.py --check
```

The shared command invokes `tools/build_grain_loader.py` and
`tools/build_grain_coworker.py`, then checks/registers their manifests and props.
Both role exporters also support `--check` independently. Gameplay review and
verification live in `docs/reviews/region_npcs/`.
