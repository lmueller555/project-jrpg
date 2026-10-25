# Liam's household and Daisy's rug — review pending

Liam, his mother, his father and Daisy are now inside their cottage in western
Eldenmere. All four use **stationary poses, with no dialogue or action routines**.

- [Actual in-game interior with the household](household.png)
- [Daisy lying on her rug — enlarged close-up](daisy_rug.png)

Liam stands beside the sleeping area, his mother faces the kitchen, and his
father faces into the dining area. Their approved idle sprites are unchanged.
Daisy rests awake on a teal-and-cream woven rug, with her original gray coat,
black/white patches, floppy ear and fluffy tail. Her still lying pose lowers
the chest, folds the legs and lays the plume alongside her body. It has one
image, without animation or behavior.

The rug is a flat, nonblocking 64×36 sprite. It is rendered below furniture and
characters. Daisy's separate foot blocker prevents walking through her body;
Caelan can walk across the unoccupied rug. The room entry, exit, furniture
access points and rug approach remain reachable with all four residents present.
Parent names remain unassigned. The household is cached with its room and is
not duplicated, moved outside or reset when Caelan leaves and re-enters.

The preview images use the real `main.py` renderer, with 2× nearest-neighbor
scaling for the room and 8× for the rug close-up. Caelan remains in the scene for
scale. Existing hearth and room lighting continue to animate normally.

## Source and rebuilding

```sh
python tools/build_liam_family_home.py
python tools/capture_liam_household.py
python -m unittest discover -s tests -p test_liam_household.py -v
```

Placement and collision probes are recorded in
`assets/maps/eldenmere/liam_house/house.json`. The rug art and source recipe are
under `assets/terrain/eldenmere/liam_home/` and
`assets/source/terrain/eldenmere/liam_home/`. Daisy's static pose and retained
parts are under `assets/characters/daisy/lying_left/` and
`assets/source/characters/daisy/lying_left/`. No approved standing or running
sprites are overwritten. Rebuilding the home also rebuilds these new assets and
retains all four stationary resident records.

The runtime's `StationaryNPC` loads one sprite and a foot blocker. It has no
update routine or conversation hooks. Social profiles, portraits and dialogue
are not added. Existing moving NPCs retain their behavior classes.

Seven household checks cover placement, absence of behavior/dialogue, stable
poses over time, player collision, exit/re-entry, reachable furniture with the
residents present, rug depth/nonblocking geometry, and native art/source-layer
reconstruction. Existing home, door, town and social checks are also exercised.
The new placement and rug are published for review and not yet merged into
`main`.

Validation: **39 focused home/door/town/social checks pass**, including all seven
household checks. The full suite passed 163 of 164; the existing Tomas schedule
check can stall near the sanctuary doorway. With seeds 0–3, untouched `main`
(`412225f`) and this branch produced identical results, including failures with
seeds 0 and 2. No NPC scheduling behavior was changed. The new assets and home
placement also rebuilt byte for byte across 62 checked files. See the
[recorded validation](validation.json).
