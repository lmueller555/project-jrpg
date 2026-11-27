# Fire Veinhold spatial continuation source

The source scene uses metres and a single Blender camera to render the shared
island, dormant volcano, fortress, reservoir, two bridges, Merovaran mainland,
distant active volcanic island and frozen-guard endpoint. This is an offline
renderer: gameplay remains Pygame and reads bounded, prerendered frame banks.

Rebuild with Blender 4.3 or newer and Pillow in the calling Python environment:

```sh
python tools/build_prologue_orbit.py --preview --samples 16
python tools/build_prologue_orbit.py --render --samples 16
python tools/build_prologue_orbit.py --check
python tools/build_prologue_orbit.py --write-recipe
```

`--segment orbit --start 0 --stop 301` permits an isolated/resumed frame export.
Proof indices can be selected with `--proof-frames 0,23,53,98,150,202,300`.
The saved, compressed `.blend` packs the referenced textures. The Python source
and `scene_config.json` own deterministic camera and plume reconstruction.
The final bank uses sixteen samples, fixed sampling seed 0 and no animated seed;
these are also the builder defaults and are recorded in the scene configuration.
Use `--blender /path/to/blender` when the executable is installed elsewhere;
Blender is an authoring dependency and is not needed to play the game.

The orbit contains **301 inclusive samples** across five seconds at 60 Hz;
the rush contains **61 inclusive samples** across one second. Their terminal
samples are handoff poses, not additional elapsed intervals. Four-second holds
use sixteen phase samples and preserve the original complete plume cycle.
Smoke follows the complete film clock starting at second 25, including the
four-second alarm hold. Both complete plume drawings remain attached to their
vents and participate in actual geometric depth occlusion.

The approved first view is reconstructed as separated spatial relief surfaces
for only the first three degrees of the orbit. Remaining orbit views use the
shared three-dimensional scene. Painted front, side and reverse views supply
UV color on eligible, unoccluded faces; unseen faces retain authored rock,
masonry and metal materials. Terrain-only source images keep windows and
banners off the geology. The frozen endpoint uses an opaque distant backdrop,
a horizontal deck and four disconnected guard/ice cutout planes at calibrated
depths. Only the source image's ground polygon projects onto the physical deck;
railings and mountains stay on the backdrop, and a steel tile fills ground
outside the reference view. Guard surfaces share no vertices with the
background, so the approach cannot pull their limbs into stretched surfaces.
The same moving camera approaches this staged view. These are matte-projection techniques, not independently
generated perspective frames or a flat image rotated through 180 degrees.

The initial local viewing direction corresponds to east-southeast in the world
atlas. The reverse view faces west-northwest. Merovar's bridge is the near
approach and the camera ends exactly **6.096 metres from its mainland landing**.
The Damar bridge has its own, separate landing and remains distinct throughout.

The brief first-view handoff gives the moon its physical proxy depth, with
soft outer and semantic matte boundaries as the camera moves. Its source image remains
unchanged; these geometric/material measures prevent doubled moon discs and
visible rectangular sky edges during the transition.

After clearing the fortress, both camera and focus descend smoothly to their
final eye-level elevations between rush seconds 0.55 and 0.80. The final rigid
stage takes over between seconds 0.60 and 0.82, before movement blur clears.
Preview PNGs are temporary authoring diagnostics and are ignored by Git;
accepted native captures live under `docs/reviews/veinhold_orbit/`.

Beauty frames contain inactive red fixtures. Parallel RGBA alarm overlays use
projected lamp locations after geometric occlusion checks. Runtime owns alarm
flashing/audio and optional rush blur/speed lines; all source beauty frames are
sharp so reduced-motion playback can reuse them.

Material and painting prompts, generation paths and hashes are recorded beside
the images under `materials/`. The original approved whole-plume drawings are
reused from `assets/story/fire_veinhold_opening/shot01/environment/` and packed
in the source scene. Asset-camera JSON files next to the exported frame banks
record every actual perspective pose and projected landmark.
