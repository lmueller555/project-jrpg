# Aldric arrival cinematic cast

These are original imagegen-authored, transparent cinematic sprites. The retained
PNG generations are unchanged. `prompts.json` records the exact descriptions and
approved portrait references. They are separate from existing overworld sprites
and do not replace any approved character artwork.

`tools/build_regent_arrival_actors.py` exports bounded cells, removes isolated
alpha matte specks, normalizes facing, registers feet and nearest-resizes the
artwork to native cinematic resolution. It does not paint limbs or scenery.
The explicit row gutters prevent neighboring cells from leaking into frames.
Each actor retains a single bodily scale across its poses.

```sh
python tools/build_regent_arrival_actors.py
python tools/build_regent_arrival_actors.py --check
```

Exports live in `assets/story/regent_arrival/actors/`. Their `animation.json`
files use a common `canvas`, foot `anchor`, static `poses`, and timed `loops`.
The caravan manifest includes its separate seated driver's attachment offset.
The side-facing horse/wagon uses a separate seated driver. Its new northbound
rear view includes the correctly back-facing driver within the illustration;
the manifest marks these poses so the runtime does not attach a second driver.

- Aldric: natural 80px adult body, navy travelling coat, gold edging, brown hair;
  standing, listening, restrained gesture, right idle, four left-walk frames,
  a rear idle and four northbound rear-walk frames.
- Guard: practical slate tunic and open cap, spear held clear in the same hand,
  admitting gesture and four stepping frames.
- Clerk, driver and local: distinct practical clothing and matching local
  dialogue portraits; the driver has separate seated and walking poses.
- Serene: brown bun, muted teal mantle, cream dress, window, turn, standing
  poses and four walking frames; Tomas: blond hair, rust vest, cups and a
  shorter 66px teenage body.
- Caravan: four side and four rear chestnut-horse walk frames, wooden provision
  wagon, turning wheels and restrained supply load. The narrow rear silhouette
  enters the southern gate facing away rather than sliding a broadside wagon
  through its wall. No regal carriage or combat gear.

The original rear sheet is retained for Aldric's back walk. Its wagon row was
refined in a separate imagegen source to occlude the far horse's body and legs
behind the rear chassis; only the wagon wheels contact the ground in this
elevated rear view. The exporter uses that revised row for the rear vehicle.

`native_review.png`, `back_review.png` and `walk_review.gif` are review-only contact artifacts.
They are not loaded by the game. Runtime `provenance.json` records source and
export hashes so source integrity and byte-identical rebuilds can be checked.

The arrival polish adds `turns_generated.png`, an original transparent two-row
three-quarter sheet. Its Aldric and complete horse/wagon poses bridge the side
and rear views; the driver is baked into every three-quarter caravan pose.
The exporter exposes `turn_left_back` and `walk_left_back` on both actors.
The first side-walk frame's original source points right, so its explicit
orientation flag mirrors it to match the other three left-facing frames.

Two additional authored caravan angles bridge the turn with native silhouette
widths of 280px (side), 221px (shallow), 155px (three-quarter), 111px (deep)
and 93px (rear). The shallow sprite uses `turn_shallow_generated.png`; the
deep sprite uses only the lower-left cell of `turn_intermediates_generated.png`.
The latter's first shallow attempt remains as source provenance but is not
exported. Both static turn poses include the seated driver, retain transparent
gutters, and use uniform nearest resizing with the common wheel baseline.
