# Authored wind-reaction artwork

Generated with `image_gen` using the existing Caelan, Lucan and Mira combat/rescue sprites as appearance references. The original generated PNGs are retained unchanged.

- `wind_men_generated.png`: 1536×1024, six columns/four rows. Caelan rear/front wind reaction occupies rows 1–2; Lucan rear/front occupies rows 3–4. Each view contains six distinct drawings: recoil, compressed brace, lift, backward flight, reaching down, and landing. Lucan starts and finishes kneeling with his left-hand shield retained.
- `mira_brace_generated.png`: 1536×1024, four columns/two rows. Four front and four rear drawings show Mira noticing the gust, planting her feet, bracing her launcher, and settling.
- `wind_right_generated.png`: 1536×1024, six columns/three rows. Six right-profile Caelan drawings, six right-profile Lucan drawings, and four right-profile Mira drawings; last two cells are empty. Side profiles were authored separately to preserve weapon hands during the camera move.
- `caelan_left_generated.png`: 1536×1024, three columns/two rows. Six individually authored left-profile Caelan wind drawings, added because his concerned turn toward Rhea exposes the opposite side during the start of the gust. His sword remains in his actual right hand, farther from this camera view.

References: `assets/story/ice_reaper_rescue/actors/caelan/ready_01.png`, `ready_rear_01.png`, `assets/story/ice_reaper_continuity/actors/lucan/hold_brace_front_01.png`, and Mira's existing `aim_01.png` / `ready_rear_01.png`.

Export is mechanical: equal-cell extraction, alpha threshold, one fixed scale per source/view, nearest-neighbor sampling, and native foot/knee registration. No joint deformation, synthesized pose interpolation or weapon mirroring is applied. Runtime supplies movement and lift through the scene.
