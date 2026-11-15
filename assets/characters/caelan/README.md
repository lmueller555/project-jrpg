# Caelan — overworld artwork and runtime registration

The runtime source of truth is [animation.json](animation.json). Normal player
travel uses the approved HD directional idles and all four approved walks.
Their existing `review_hd/` paths remain stable; no approved PNGs were moved
or redrawn for integration.

| Bank | Artwork pixels | Logical canvas | Timing | Runtime state |
| --- | --- | --- | --- | --- |
| Directional idles | 48×72 | 24×36 | Stationary | Integrated, approved |
| Four directional walks | 48×72 | 24×36 | 16×35ms =560ms | Integrated, approved |
| Four directional runs | 24×36 | 24×36 | 4×100ms =400ms | Retained legacy artwork |
| Carrying/actions/cinematic bodies | Bank-specific | Existing registration | Existing cues | Scene-owned legacy artwork |

The logical draw anchor remains [12,30], the foot anchor [12,34]. HD artwork
records use their corresponding [24,60]/[24,68] artwork anchors. Movement speed,
collision, interaction distance, world positions and camera coverage stay as
before. Ordinary travel has no separate sword/tool overlay.

`Player` loads each declared bank through the shared density-aware loader.
HD frames remain native in WorldCanvas composition while their logical mirror
stays24×36. Each idle/gait reference declares its own density: the root record
does **not** apply density2 to the legacy runs. There is one authored animation
clock, and idle/turn/gait reset behavior remains unchanged.

Scene actors copy mutable banks and authored durations rather than changing the
player's data. Ordinary inherited travel uses the HD frames and35ms timing.
Explicit scene banks retain their own poses, anchors, cues and durations.
SanctuaryReturn's cup grips retain an explicit legacy carrying bank, including
free movement while holding cups; releasing the scene restores normal HD travel.
Bespoke rescue/support, seated, household and cinematic artwork remains legacy
until rebuilt separately. Running and action transitions therefore still change
pixel detail temporarily.

[Integration captures, compatibility checks and limitations](../../../docs/reviews/caelan_walk_integration/README.md)
include real Player movement in town, Sanctuary hall and the cave. The approved
stride does not fully cancel world travel at72 world units/s; the measured
side-view sole-span diagnostic shows about11 render pixels of residual drift
through the sampled stance. This is a rolling contact proxy, not an ankle-lock
measurement. The integration preserves approved art,560ms timing and gameplay
speed; stride refinement is separate artwork work.

## Sources and rebuilds

Sources and exact registration remain alongside the existing approved packs:
[idles](review_hd/idles/idles.json), [front](review_hd/walk_front/animation.json),
[rear](review_hd/walk_back/animation.json), [left](review_hd/walk_left/animation.json),
[right](review_hd/walk_right/animation.json). Integration status is retained on
re-export; historical approval/reference hashes still protect exact PNG pixels.

```sh
python tools/export_caelan_hd_idles.py
python tools/export_caelan_right_walk_hd.py
python tools/export_caelan_left_walk_hd.py
python tools/export_caelan_front_back_walk_hd.py
```

The earlier24×36 files and combined direction sheets remain available for the
legacy runs and scene dependencies. Rebuild that retained bank with
`python tools/build_caelan_overworld.py --check` (or omit `--check` to export).
That builder does not replace the HD runtime registry. Older review documents
retain historical captures and local construction evidence; the
[global visual standard](../../../docs/VISUAL_ART_STANDARD.md) remains the
single authoring and rendering guide.
