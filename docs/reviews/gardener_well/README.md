# Sanctuary gardener — well routine review

Status: awaiting user review. Implemented in the playable town launched by `main.py`.

Superseded by the [centered near-side revision](../gardener_near_side/README.md). The user liked the well operation but requested removing the unsupported lateral bucket transfer. These captures retain the earlier two-bucket proposal for comparison; the live game and capture command now use the centered near-side routine. The rejected intermediate side-loading attempt remains in `../gardener_single_bucket/`.

- [Drawing water, 6× looping close-up](well_drawing.gif): set down her empty pail, approach the crank, lower the well bucket, dip/fill, reverse the crank to raise it, secure the windlass, guide the bucket over the front opening, transfer the water, reset and pick up her full pail.
- [Full watering trip](full_routine.gif): native-scale overview of the actual lane, sanctuary stairs and well. Travel and work run at game speed; only the long initial rest is shortened. This overview is captured at 5 FPS; action close-ups use 10 FPS.
- [All six watering stops, 6×](watering.gif): four flower patches and both raised window troughs. This montage cuts between consecutive stops; the full-trip preview includes the walks between them.
- PNG fallbacks: [well](well_drawing.png), [route](full_routine.png), [watering](watering.png).

The active trip takes about 89 seconds. The random 180–300 second rest remains unchanged and is sampled once per break. She uses the western village lane and both directions of the sanctuary stairs; she no longer collects water at the brook.

The rope-mounted bucket and portable pail are separate objects. Her pail remains empty throughout lowering, dipping and raising; six portions transfer only during the visible downward stream. Those six portions then decrease by one at each watering target. The well bucket returns empty to the same parked position each trip. Crank rotation reverses for the loaded ascent, and her registered hand follows its handle. The front stone lip masks the bucket inside the shaft; the bucket passes over the front opening before moving right to clear the timber post.

The well reserves one operator. Gardener actions and mechanism phases use one fixed-step clock; there is no independent bucket-lifting loop. A parked pail has a small ground blocker clear of the south through-path. She waits when Caelan occupies a workstation and resumes when it clears. Entering an interior preserves the actor, well reservation, rope/bucket phase, water and rest countdown; work continues while outside the active view.

Rebuild and capture:

```bash
python tools/build_well_drawing.py
python tools/capture_gardener_well.py
python -m unittest discover -s tests -v
```

The exporter registers moving parts against the approved well and derives work poses from the approved female_02 appearance. Source art, ordinary walking sprites, town terrain and building positions are preserved. `drawing_recipe.json` records the well registrations. Runtime rendering requires Pygame only; Pillow is used by the exporters and preview tools.

The preview uses a seeded random generator for reproducibility; live games use entropy. `capture.json` records phase transitions, positions, water quantities and rest samples. GIF encoding checks decoded pixels and timing against the runtime captures. Historical brook previews remain in `../sanctuary_gardener/` as the previous approval record.
