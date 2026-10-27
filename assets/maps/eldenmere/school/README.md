# Eldenmere school — approved

The school is on lower ground northeast of the well square, south of Mira's
workshop and west of the stream. Its native exterior origin is [576,528], with
a 6×4-tile ground footprint [600,624,144,96]. A short dirt forecourt and path
connect its south-facing entrance to the well square. A broadleaf shade tree,
bench, flowers and shrub reuse the approved 5.4-second breeze animations.
Existing building positions, river geometry and terrace elevations are retained.

`layout.json` is the placement source. The school has eighteen 300 ms exterior
phases and five proximity-door patches. Door anchor [672,726] opens/holds/closes
through the existing runtime behavior. Entering loads the separate 16×12-tile
classroom; its courtyard exit returns to [672,738]. The map landmark is
“Village school”. Running `main.py` makes the building directly explorable.

The classroom contains three shared desks, six pupil chairs, a teacher's desk
and chair, writing board, book shelf, village map, children's drawings, coat
pegs, reading bench, festival supplies and a hearth. The center aisle and all
nineteen furnishing approaches are reachable with Caelan's normal footprint.
Daylight and hearth light animate; classroom objects retain their own depth
and collision registration.

Liam's mother is the teacher, recorded in the room and family metadata. This
stage adds the building and furnished interior. Ordinary teaching, pupil attendance and
commuting schedules remain unassigned. MQ04 temporarily borrows the existing
teacher and six children for a festival preparation session, then takes Liam
and Tomas on their agreed workshop outing. This quest attendance does not
install a general school-day simulation. See [the quest guide](../../../../docs/LANTERN_QUEST.md).

```sh
python tools/build_eldenmere_school.py
python tools/capture_eldenmere_school.py
python -m unittest discover -s tests -p test_school.py -v
```

The school compiler edits its own room and local town addition. The canonical
`tools/build_building_interiors.py` also reapplies it after the family extension,
so a full town/interior rebuild retains the school. Source layers and recipes
live with the exterior and interior packs under `assets/source/terrain/eldenmere/school`.
See [review captures](../../../../docs/reviews/eldenmere_school/README.md).
