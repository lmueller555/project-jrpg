# Aldric arrival cinematic cast

The original imagegen-authored, transparent cinematic sheets are retained
unchanged. `prompts.json` records their descriptions and approved portrait
references. Aldric's corrected side walk is a separate, offline part-authored
source in `aldric_side_walk/`, built from those retained appearance pixels; it
is not a new image generation. The clerk's `clerk_walk/` source separately
authors native side/quarter/rear steps and foreshortened aerial views from his
own retained appearance. Overworld sprites and portraits are unchanged.

`tools/build_regent_arrival_actors.py` exports bounded cells, removes isolated
alpha matte specks, normalizes facing, registers feet and nearest-resizes the
artwork to native cinematic resolution. It does not paint limbs or scenery.
The explicit row gutters prevent neighboring cells from leaking into frames.
Each actor retains a single bodily scale across its poses.

```sh
python tools/build_aldric_side_walk.py
python tools/build_regent_clerk_walk.py
python tools/build_regent_arrival_actors.py
python tools/build_regent_aerial_actors.py
python tools/build_aldric_side_walk.py --check
python tools/build_regent_clerk_walk.py --check
python tools/build_regent_arrival_actors.py --check
python tools/build_regent_aerial_actors.py --check
```

Exports live in `assets/story/regent_arrival/actors/`. Their `animation.json`
files use a common `canvas`, foot `anchor`, static `poses`, and timed `loops`.
The caravan manifest includes its separate seated driver's attachment offset.
The side-facing horse/wagon uses a separate seated driver. Its new northbound
rear view includes the correctly back-facing driver within the illustration;
the manifest marks these poses so the runtime does not attach a second driver.

- Aldric: natural 80px adult body, navy travelling coat, gold edging, brown hair;
  standing, listening, restrained gesture, right idle, eight left-walk phases,
  a rear idle and unchanged four-frame rear and rear-three-quarter walks.
- Guard: practical slate tunic and open cap, spear held clear in the same hand,
  admitting gesture and four stepping frames.
- Clerk: 77px adult, retained moss coat/brown hair and closed ledger in the
  anatomical left hand. Eight phases each for side, rear-quarter and rear
  walking, with a 30px full stride, steady carrying arm, opposing free-arm
  swing and exact retained side head pixels. Static back/turn and separate
  native 48×64 aerial views keep convoy staging continuous. Original standing,
  reading and portrait PNGs are unchanged; unseen rear shapes are documented
  as native reconstruction, not generated or user-approved art.
- Driver and local: distinct practical clothing and matching dialogue portraits;
  the driver has separate seated and walking poses.
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
The old side-walk sources remain unchanged, including the originally right-facing
first pose. They are no longer used for the side loop. The new native source
shares one head/torso appearance, fixed-length limbs, explicit support/swing
phases and fixed pelvis registration; no moving-foot recentering or per-frame
mirroring is applied. A 32-pixel full stride controls playback from actual ground
distance, including the aerial reference handoff. Aldric's rear loops retain
their original clock-based playback. See the [side-walk review](../../../../../docs/reviews/aldric_side_walk/README.md).

The later [clerk/crossroads review](../../../../../docs/reviews/regent_crossroads/README.md)
adds independent distance-driven clerk loops, not a recolored Aldric. The Aldric
protection inventory exempts only the clerk manifest and new locomotion files;
it still guards the original clerk idle, reading and portrait assets. The clerk
source inventory separately protects all original Aldric art.

Two additional authored caravan angles bridge the turn with native silhouette
widths of 280px (side), 221px (shallow), 155px (three-quarter), 111px (deep)
and 93px (rear). The shallow sprite uses `turn_shallow_generated.png`; the
deep sprite uses only the lower-left cell of `turn_intermediates_generated.png`.
The latter's first shallow attempt remains as source provenance but is not
exported. Both static turn poses include the seated driver, retain transparent
gutters, and use uniform nearest resizing with the common wheel baseline.
