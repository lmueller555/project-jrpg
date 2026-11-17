# Elden Vale Rising Rain — staged asset review

PR 3 completes the staged regional asset series. It does not activate weather,
NPC schedules, animal routes or atlas markers. These are offline compositions,
not gameplay captures or user visual approval. See the
[regional design](../../world/regions/ELDEN_VALE.md),
[terrain maintenance reference](../../TERRAIN_ART_STANDARD.md#staged-elden-vale-rising-rain)
and [visual standard](../../VISUAL_ART_STANDARD.md#staged-rising-rain-actions-and-wildlife).

## Effects and environment

- [Asset board](asset_board.png): sixteen water/atmosphere drawings, separate
  cloth/post/leaf props, complete action poses, bird drawings and map donors.
- [Daylight sequence](meadow.gif), [half-speed sequence](meadow_slow.gif) and
  [dark-background sequence](dark_woodland.gif) show signs, arrival, peak and
  departure. Their twelve-second clock is an illustrative review timeline,
  not the production recurrence or quest trigger.
- [Daylight peak](meadow_peak.png), [dark peak](dark_woodland_peak.png), and
  [dedicated reduced-motion still](reduced_motion.png) retain exact PNG artwork.
- [Collection station](collection_station.png) has separate fixed posts, ties,
  panels and a washing basket. No ordinary prop receives discovery cues.

Effects use hard masks and declared layer opacity. Veils intentionally use a
lower source-alpha threshold and restrained whole-layer translucency; this is
not an accidental soft-alpha fringe. Particle instances ascend from wet ground,
with deterministic independent offsets and a protected central interaction band.
High mist and still states are separate drawings. The phenomenon remains distinct
from confluence motes, lightning and combat/status effects.

## Character actions and birds

| Action | Drawings and contacts | Motion |
| --- | --- | --- |
| Gather washing — existing female_01 gardener | [Poses](gather_poses.png), [contacts](gather_contacts.png) | [Normal](gather.gif), [half speed](gather_slow.gif) |
| Deploy collection cloth — existing male_02 picker | [Poses](deploy_poses.png), [contacts](deploy_contacts.png) | [Normal](deploy.gif), [half speed](deploy_slow.gif) |
| Catch a droplet — Liam identity study | [Poses](leaf_poses.png), [contacts](leaf_contacts.png) | [Normal](leaf.gif), [half speed](leaf_slow.gif) |

Each action has eight complete redrawn right-facing poses, one uniform source
scale, stable sole registration and separately registered props. Adult and child
body heights preserve the original idle silhouettes' logical heights. Approach
uses existing legacy right-walk frames for compatibility reference only, followed
by the new work poses; those walks are not new HD gait assets. Normal action GIFs
play once, so resetting a review does not imply an ongoing world-object loop.
The cloth's far corner is pre-tethered before the picker secures the near corner.
The held leaf uses the horizontal cupped orientation so Liam's face remains clear.

Preview ownership is seekable and stateless: one object appears at the station
or grip, transfers at an authored cue, and never exists in both. Gathering ends
in an explicit carrying hold, deployment leaves its panel at the station, and
the leaf is returned after lowering. No personal tool remains in ordinary travel.
These are reference action banks, not new cast placements or a committed Liam
outing. Integration must give the props authoritative production owners, facing,
world depth, interruption/Continue handling and appropriate availability.

The brown/cream regional bird retains its identity and original physical body
height. See [all poses](bird_poses.png), [departure](bird_departure.gif),
[flight loop](bird_flight.gif) and [slow flight](bird_flight_slow.gif). The sixteen
complete drawings cover perch/alert, takeoff and an eight-frame flight cycle.
Registration follows the cream breast rather than the changing wing bounds;
flight trajectory stays separate from anatomy. Reduced motion uses a stable perch.
No existing animal ID, route, save or other wildlife bank is replaced.

## Cartography and reproducibility

[Map symbols](map_symbols.png) derive the antlers and ruined arch from PR 2.
A Rising Rain symbol is exported as an optional candidate only. Icons retain
64×64 cartographic slots, independent of world-density conversion. No marker,
forecast feature or atlas regeneration is activated before the layout is integrated.

Rebuild with `python tools/build_elden_vale_rising_rain_hd.py`; add `--check` for
non-writing byte comparisons. Retained sources, generation briefs, identity board
and dependency hashes live under
`assets/source/terrain/overworld/elden_vale/rising_rain_hd/`. The builder needs no
external generation service. GIFs use a shared palette and centisecond-aligned
delays; PNGs are authoritative for exact colors and alpha.

Focused tests cover upward/bounded/deterministic particles, still presentation,
single-owner handoffs and seeking, frame/sole/grip registration, fixed support
pixels, density/alpha/icons and encoded GIF timing. Gameplay integration must
still implement a reliable first encounter, event cadence, pause/focus/exit
lifecycle, reduced motion, actual occlusion/lighting, camera/save behavior and
performance review. There are no rewards, elemental modifiers or new lore facts.
