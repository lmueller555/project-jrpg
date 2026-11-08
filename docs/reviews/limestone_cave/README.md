# Limestone cave chamber review

**Proposed asset pack and isolated review chamber; not merged into main.**

![Limestone chamber](chamber_lit.png)

The screenshots use the production `Player` and `SanctuaryCaveWorld` renderer.
Caelan reaches each review station by ordinary collision-checked walking or
running. The viewer does not load a journey, quest or settings file.

Many tiny red, blue, green, white, orange and purple microcrystals are embedded
through the cave walls. They follow irregular fissures and mineral seams,
with dense little pockets and sparse grains between them. Individual facets
remain only a few native pixels across, visibly small beside Caelan. The same
slow pulse brightens these grains and their local environmental illumination.
The chamber places **504 individual grains across 18 seam fields**, with 84
grains of each color. Most facets are 2 × 3 native pixels; none exceeds 4 × 5.

- [Whole chamber](whole_chamber.png): stitched production world views at one
  shared light clock, enlarged with nearest-pixel scaling.
- [Material colors](chamber_material_colors.png) and
  [crystal lighting](chamber_lit.png): the same reached pose and camera with
  the environmental light pass toggled.
- [Pulse trough](pulse_trough.png) and [pulse crest](pulse_peak.png): the same
  standing position during one complete six-second pulse.
- [Animated crystal pulse](crystal_pulse.gif): native logical resolution.
- [Microcrystal seams and scale](embedded_wall_gems.png): six colored wall
  details cropped from the production-renderer overview at one shared light
  clock. Each view and Caelan are enlarged exactly three times, so the tiny
  facets can be compared with his height.
- [Microcrystal module board](../../../assets/terrain/limestone_cave/wall_gems/colors_review.png):
  the red, blue, green, white, orange and purple seam variants at a common scale.
- [Walkthrough](chamber_walkthrough.mp4): dry and wet surfaces, the tunnel,
  keeper ledge and formations, followed by a full pulse.
- [Reduced motion](reduced_motion.png): readable static crystal illumination.
- [Material board](../../../assets/terrain/limestone_cave/materials_review.png):
  unlit asset study, source stone and Caelan at a common native scale.
- [Regional comparison](../../../assets/terrain/limestone_cave/regional_comparison.png):
  the proposed rock alongside existing Sanctuary and Eldenmere materials.
- [Contact sheet](contact_sheet.png): labeled production views for comparison.

The view labeled material colors deliberately omits the light pass to show the
underlying stone palette. It is not a different drawing of the room. The
contact sheet and module board are labeled comparison layouts; other images
come directly from the playable renderer.

Play with `python tools/preview_limestone_cave.py`. WASD/arrows move, Shift runs,
Space holds the pulse, L toggles material colors, R toggles reduced motion,
H hides the guide and Escape closes the viewer. No normal game map is changed.

Reproduce with `python tools/capture_limestone_cave.py`; use `--check` to verify
the retained source and artifact fingerprints. `verification.json` records the
reached stations, six microcrystal colors and grain counts, movement modes,
light brightness range, reduced-motion check and unchanged production-file hashes. See the
[review guide](../../LIMESTONE_CAVE_REVIEW.md) for the asset rebuild commands.
