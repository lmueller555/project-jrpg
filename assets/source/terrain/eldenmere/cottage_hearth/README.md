# Eldenmere animated cottage hearth source — review

A plain warm-gray stone hearth with a narrow chimney breast, rectangular lintel, dark opening, two fixed logs, restrained flames and glowing coals. Its 48×72 frame fits the 24px terrain grid and original 24×36 character scale. Four source-drawn fire poses run for 300ms each (1.2 seconds). Stone and log geometry stay fixed; only fire, coal colors and subtle local lighting change. Smoke travels through the chimney; no indoor smoke sprites are included.

`hearth_concept.png` is the committed generated source, originally `/workspace/generated_images/exec-baf1eeba-6b54-4767-9925-43dcf1847993.png`. The approved furnished room supplied the visual reference. The sheet retains a separate firebox, chimney and four flame clusters. Crops, native sizes and registration are explicit in `recipe.json`; rebuilding does not require the original workspace path.

Export uses nearest-neighbor sampling and named material palettes. Magenta is removed when red >160, blue >120, and both exceed green+70. Chimney samples map only to the approved stone ramp; firebox samples map to stone, wood, soot and ember colors; flame samples map to the four-color fire ramp. No smoothing, dithering or fractional-alpha sprites are used. Native samples are retained under `parts/` here and in the runtime pack.

Assembly: the 16×36 chimney sits at (16,0), the 44×32 firebox at (2,36), and the 14×14 flames at (17,44), all within 48×72. The four flame crops share the same vertical source registration so differing tips preserve their source height. The 192×72 atlas contains four full frames. `structure.png` is the static source-derived body with its coal marker color; it is not an extinguished interaction state.

Three native masks mark the union of source flame pixels, original coal-color pixels and stone near the opening. Only those areas vary across full hearth frames. Stone around the opening mixes 6–9.5% toward amber across the four phases; coals cycle through four subdued red/orange colors. The floor glow has fixed geometry, two discrete low-intensity bands, and preserves the existing plank texture by mixing each underlying floor color. The L-mode floor mask uses 0/128/255 as intensity labels; exported RGBA overlays still use only 0/255 alpha.

The hearth sits at (28,24) in the existing 288×288 illustrative room. Its narrow chimney fits between the northwest timber support and left window; the broader firebox begins below the window. Its suggested local floor footprint is (2,48,44,20). Existing windows, door, furniture, storage and Caelan remain clear. The floor glow stays within (30,89,46,21), ending before the bed; the 72px central path stays open. This remains an art-review arrangement, not a named residence or final map.

The builder reads all approved packs without rewriting them. The room draws structure, approved daylight, floor firelight, approved furniture, approved storage, hearth and original Caelan. The 1.2-second fire and unchanged 5.4-second daylight share a 10.8-second full scene loop: 36 frames at 300ms, with each existing daylight pose held for its original 600ms. GIFs are lossless nearest-neighbor enlargements, 4× for the room and 8× for the hearth close-up.

Build: `PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/project-jrpg/bin/python tools/build_eldenmere_cottage_hearth.py`.

Check with the same interpreter and `tools/test_eldenmere_cottage_hearth.py`. The hearth design and animation await review. Collision, extinguishing/lighting interactions and named household layouts remain future work.
