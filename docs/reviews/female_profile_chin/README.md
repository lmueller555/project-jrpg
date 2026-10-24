# Female NPC profile chin cleanup

Status: awaiting user review.

- [Enlarged before/after face comparison](faces_before_after.png): all three palettes, both profiles. Each before face is immediately followed by its after face.
- [Left walking comparison](walk_left_before_after.gif): synchronized before/after pairs for blue, sage and plum.
- [Right walking comparison](walk_right_before_after.gif): the same comparison facing right.
- [Gardener carrying profiles](gardener_carry_profiles.gif): corrected heads with empty/full bucket attachments.

Each profile changes **three opaque outline pixels** into existing skin shades. The small jaw cluster beneath the iris is filled with one skin-base pixel and two warm skin-shadow pixels, giving a neutral closed-mouth expression. Pupil/iris colors, hair, alpha, silhouette and all other native pixels remain identical. The 24×36 walks retain their four 140ms phases and coordinated head/shoulder bob.

The base directional exporter records the cleanup landmarks in its source recipe. Both palette variants derive from those corrected profiles, and the gardener's carrying and working poses are rebuilt from the same appearance parts. Her approved route, watering, water quantities and 3–5-minute rests are unchanged. Existing sanctuary-gardener scene previews remain the historical approval record for that routine.

`before/` retains original native idles and walk frames from commit `8c8daed83dc959e171c6c8d59af89fb6429d163f`. `comparison.json` records that baseline. Recreate these presentation boards with `python tools/review_female_profile_chin.py` using the Pillow asset environment. The carrying comparison uses the shared 140ms pose timing; in-game carrying motion advances by distance.

Rebuild the affected appearances in this order:

```sh
python assets/source/characters/npcs/female_01/directions/export_idles.py
python tools/build_female_npc_palette_variants.py --direction left
python tools/build_female_npc_palette_variants.py --direction right
python tools/build_dress_walk.py --direction left
python tools/build_dress_walk.py --direction right
python tools/build_female_npc_walk_variants.py --direction left --allow-review-base
python tools/build_female_npc_walk_variants.py --direction right --allow-review-base
python tools/build_gardener.py
```

The explicit review flag lets the palette builder derive comparison previews from the revised base while its appearance awaits approval. Ordinary generation still requires an approved base. Aggregate direction boards can be refreshed through the existing `build_direction_sheets`, `build_direction_board` and `build_grid` helpers without regenerating front/back sprites.

`python -m unittest discover -s tests -v` checks that each idle and walking phase changes only those three pixels, that alpha/eyes/stride stay intact, and that the gardener's visible profile heads use the same correction, alongside the game and routine checks.
