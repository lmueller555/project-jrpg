# Eldenmere cottage interior source — approved

`materials_concept.png` retains the generated architectural source for the cottage timber, window and inside-facing door. Its original remains at `/workspace/generated_images/exec-f3f7c32f-62f3-4c18-852b-2774ee5456c7.png`. `materials_quiet.png` supplies three floor appearances and the plaster face; its original remains at `/workspace/generated_images/exec-828a5fcd-12fb-4b35-8153-4af16b51f359.png`. Both committed images make rebuilding independent of those workspace paths. The kit follows the approved cottage wood, cream plaster, stone, iron and muted glass colors.

Interiors use larger, separate room maps, as selected by the user. This first milestone establishes reusable foundations in an illustrative room with a 10×8-tile floor, independent of exterior cottage footprints. It is unfurnished and is not assigned to Caelen or a named household. The narrative files, outdoor review scenes, and character assets remain read only.

`recipe.json` records each source file/crop, native size, material rules, room registration, windows, doorway and daylight timing. Nearest-neighbor sampling and explicit magenta removal produce binary-alpha source parts. Floor red-channel thresholds `[124,169,194]` separate dark joints, broad base faces and sparse highlights without amplifying source shading into noisy grain. Other materials use nearest named RGB colors; cool glass and the door's small hardware landmark receive their own ramps. `parts/` retains all eight native components. Three floor tiles share an 8-pixel plank-row pitch with staggered joints.

Reusable tiles include three 24×24 floors, two 24×48 north wall appearances, upper corners, projected 24×24 side walls, low front caps/corners and a 24-pixel entry threshold. Walls assemble from source plaster and timber; corner/side orientation changes preserve native pixels. The threshold reuses the approved cottage's exact native stone-step crop `[48,138,72,144]`. The tile atlas uses seven columns of 24×48 padded slots; metadata records each actual image rectangle.

The review is a 288×288 cutaway room: a 240×192 floor, 48-pixel north wall, narrow side walls and low south cap with a 24-pixel entry. Source timber supports define broad bays, two 24×30 windows supply daylight, and a 24×36 closed door demonstrates an adjoining-room appearance. This door is not the open south exit and has no interaction animation in this milestone. Unchanged Caelan provides 24×36 character scale.

Window glass pixels project onto a fixed floor mask, preserving the gaps cast by mullions. Three named daylight ramps gently change the colors of the existing floor pattern by small amounts; no geometry moves. Nine 600 ms poses give a 5.4-second loop. All runtime pixels have hard alpha, and structural layers and character pixels remain fixed. GIF frame differences preserve exact nearest-neighbor pixels/timing, merging held poses where possible.

Build: `PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/project-jrpg/bin/python tools/build_eldenmere_cottage_interior.py`.

Test: use the same interpreter with `tools/test_eldenmere_cottage_interior.py`.

The interior foundations, floor scale and daylight animation are approved. Furniture, room identities, working door transitions and engine collision/navigation remain future work.
