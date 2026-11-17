# Interior doorway readability

Compared with main at `1e39f7b2`. The 2× game art and the existing orthogonal
camera are retained. The paired crops come from the production `Game.draw`
renderer at 960×640, with matching valid position fixtures, camera and clock
settings; the crops are not rescaled or retouched.

- [South exits: before and after](south_exits.png). Timber rooms use fixed
  wall returns, a stone sill aligned to the existing transfer point, and a
  short glimpse of packed earth, paving or the connecting hall's floor.
  The Sanctuary reserve exit and the narrower relief-room return use masonry
  and different landing treatments.
- [Open doors and inn stairs: before and after](doors_and_stairs.png). Five
  registered poses share the same leaf, frame and approach; the timber or stone
  interior remains behind the opening, with a sill visible through every pose.
  At the inn, bright risers suggest ascent; the upper floor has a recessed,
  shaded well. The stair chevrons are gone. Both are still approached from the
  south landing, just as before.

The camera, scene registrations, paths, collision masks, triggers, arrival
positions, door timings, furnishing records and quest data were not changed.
These changes are authored in the existing town and reserve builders, not by
patching live sprites or adding HUD prompts.

[Full native room view: Liam’s house](liam_house_native.png).
