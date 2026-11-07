# Mira combat redraw

`mira_combat_authored.png` is the complete, unchanged imagegen source atlas:
six columns, seven rows, and 42 whole-body drawings. The retained references
and exact generation prompt are recorded in `generation.json`.

The character follows Mira's established ponytail, cream flower, dusty pink
rolled-sleeve shirt, charcoal trousers, boots, and tool pouch. Her compact
spring-powered launcher keeps the existing wood/iron/brass design.

Rebuild the native bank with:

```sh
python tools/build_mira_combat.py
```

The shared `build_machinist_assets.py` and `build_mill_combat_assets.py` entry
points also dispatch Mira to this builder. They retain the previous world
launcher prop byte for byte and leave Rivet's source and exports unchanged.

`registration.json` contains explicit anatomical projected floor positions,
chosen against the supporting boots and pelvis rather than the silhouette's
center of mass. Its `source_foot` and attachment points are cell-local;
`source_rect` is the global source cell rectangle `[left, top, width, height]`.
The exported frame records also retain global `source_bounds` as
`[left, top, right, bottom]`, crop destination `position`, and source SHA256.

The builder selects the main connected opaque component of each drawing,
excluding detached source projectile art and antialias fringe. One fixed
0.225 scale, nearest-neighbor sampling, binary alpha, and a shared 96-color
palette derived only from opaque source pixels are used for the whole bank.
Invisible source RGB cannot displace the shirt's dusty rose colors from this
palette. It does not redraw, stretch limbs, or
rescale poses independently. All production frames use a 64×64 canvas and
the same `[32,54]` floor anchor. Frame-local muzzle and controller points
drive the runtime's mechanical effects.

The 42 drawings cover four idles, eight shot phases, two guard entries, two
held guards, four guarded impact/recovery phases, four hurt/recovery phases,
six Overclock phases, four victory phases, four defeat phases, and a four-pose
walk. Victory and defeat hold their final poses. The first three guarded
impact phases are not a replacement for the held guard loop.

Bolt Shot retains its 800 ms action and 400 ms damage event. Its authored
release occurs at 280 ms; the scene renders the projectile from its release
muzzle to the authoritative hit point over the remaining 120 ms. Overclock
retains its 900 ms action and 500 ms application. These drawings do not alter
Mira's attributes, costs, ATB, or Rivet's deployment/Haste rules.
