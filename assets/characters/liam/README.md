# Liam — approved directional idles

Liam is **8 years old**. The approved design uses tousled chestnut hair, two
green eyes, an ochre tunic with green collar, brown breeches and small boots.
His front idle has empty hands and a relaxed standing pose.

`idle_front.png` is a transparent 24×36 frame, with 12×26 occupied bounds and
foot anchor `[12,34]`. `idle_front.json` records the design, source layers,
eyes and frame registration; `palette.json` records the limited colors.

Build using `python tools/build_liam_family_idles.py`. His parents and the
enlarged comparison are linked in `../liam_family/README.md`. The front idle is
approved; no world placement or dialogue has been added.

## Left, right and back — approved

`idle_left.png`, `idle_right.png` and `idle_back.png` retain Liam's 26 visible
pixels and 24×36 frame, green collar, ochre tunic, breeches and boots. Profiles
have one green eye and skin-colored chins; back has no visible eyes. The
approved front and palette are unchanged. `idle_all.png`/`idle_all.json` combine
front, left, right and back with independent approval status.

Build with `python tools/build_liam_family_turnarounds.py`; see the
[turnaround review](../../../docs/reviews/liam_family_turnaround/README.md).

## Front walk — approved

`walk_front/` adds a four-frame, 140 ms shared-stride front walk. Liam keeps his
approved face, collar and short-breeches costume. Registered child-sized arms
and legs follow the adult phase sequence; head and shoulders bob together.
See the [looping review](../../../docs/reviews/liam_family_front_walks/README.md).

## Left, right and back walks — approved

`walk_left/`, `walk_right/` and `walk_back/` each contain four 140 ms walking
frames, a native strip, animation metadata and a reproducible pose recipe.
Approved directional appearances, palettes and front walks remain unchanged.
See the [enlarged synchronized previews](../../../docs/reviews/liam_family_directional_walks/README.md).
All four walking directions are approved; no world placement is added.

## Left-facing run — approved

`run_left/` adds a four-frame run prototype at 100 ms per frame. See the
[normal-speed, slow-motion and walk/run comparisons](../../../docs/reviews/liam_daisy_run_prototypes/README.md).
The left run is approved; approved idles and walks are unchanged.
