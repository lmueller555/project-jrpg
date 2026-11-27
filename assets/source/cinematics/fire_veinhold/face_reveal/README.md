# Fire Veinhold frontal reveal — source assets

This bank supplies the five-second frontal running reveal at reel seconds
42–47. The [scene owner](../../../../../docs/narrative/scenes/FIRE_VEINHOLD_PROLOGUE.md)
owns its staging; the [sprite standard](../../../../../docs/SPRITE_ANIMATION_STANDARD.md)
owns animation authoring. These are local production facts, not another style
or motion standard.

## Character drawings

The active selections are `lucan/source_art_48.json`,
`iselin/source_art_48.json` and `crown_soldier/source_art_48.json`.
Each selects 48 complete image-authored RGBA drawings in an 800 ms cycle.
Lucan and the soldier use 768×1024 with anchor `[384,960]`; Iselin uses
1024×1024 with anchor `[512,960]` for her wider flowing silhouette.
The older 24-pose profiles, masters and original review remain historical.
Source-cell landmarks and
uniform whole-figure sampling register the paintings without independently
moving limbs, pasting portrait heads or normalizing occupied bounds.

The rendering target is the frozen guards' detailed painted fantasy treatment:
natural proportions, modeled surfaces, readable metal/leather/cloth and cool
moonlight. Approved character designs supply facial identity, hair, costume
sides and equipment. The preceding side-view bank was approved for a cropped
lower-body shot; it does not supply the frontal faces or upper-body acting.

Retained prompts, original generated masters, appearance/motion references and
generation records document the drawings. Any alpha-only cleanup retains the
original master and its recorded recipe; the active profile identifies the
actual selected derivative. Unselected pilots and backups remain history.

The contact labels retain the shared Foley vocabulary: `near` is anatomical
right at pose 0 and `far` is anatomical left at pose 24, including in this frontal
view. The front shot starts at poses 36, 46 and 6 for Lucan, Iselin and the
Crown soldier respectively, continuing the preceding three seconds of running.
It does not restart all three actors at pose 0. Eye direction remains steady;
the short repeating cycle contains no repeated blink or deliberate glance.

From the repository root:

```sh
python tools/export_prologue_faces.py
python tools/export_prologue_faces.py --check
```

`--actor lucan`, `--actor iselin` or `--actor crown_soldier` limits the export.
Individual runtime PNGs remain native. Review sheets provide uniformly reduced
complete figures and source-resolution face crops. Their registration,
source hashes and exporter hash are recorded with the runtime frames under
`assets/story/fire_veinhold_opening/shot07/characters/`.

## Environment and camera

The environment folder retains generated sky/coast, wet steel deck and
transparent railing paintings. The offline environment exporter projects those
surfaces with the same `camera_at` and `project_world` helpers that place the
characters in `cinematic_face_reveal.py`. It composites complete drawn figures
over freshly projected scenery offline. Runtime streams the final native frames
through eight slots (at most 18.75 MiB including pending reservations) and keeps
no separate actor image bank. This avoids increasing runtime RAM with the richer
source drawings. A baked marker and portable performance signature reject stale
camera/pose-clock/pixel contracts. Completion and scene close release the images.

The camera moves ahead of the party toward the fortress while looking back
toward Merovar. Its essential downward tilt reveals their faces. Anatomical
right appears on viewer left. The soldier's 3.048 m trailing gap is projected in
depth, preserving perspective rather than moving him forward for the frame.
Normal and Reduced Motion retain this essential reveal and the same gait clock.

The 301 environment samples include both ends of five seconds at 60 Hz; the
shot displays 300 frames. Sources, geometry parameters, camera metadata and
runtime hashes remain alongside the environment's export recipe. Native
production and slow review captures are under
`docs/reviews/veinhold_running_polish/`. The earlier
`docs/reviews/veinhold_face_reveal/` captures retain their original revision.
