# Female NPC — directional idle source

Status: original appearances and palettes approved by the user. The left/right profile-jaw cleanup is awaiting review; back appearances retain their approval.

`turnaround_concept.png` is the generated appearance source, guided by the approved female front and the established male directional scale. Its 512-pixel panels are left, right and back. Each shows the low bun, short-sleeved blue dress, exposed calves and ankle boots. The back has no face or eyes.

Run from the repository root:

```sh
python assets/source/characters/npcs/female_01/directions/export_idles.py
python tools/build_female_npc_palette_variants.py --direction all
```

The source exporter thresholds alpha at 128, uses nearest-neighbor sampling and maps each body band into the approved named material ramps. Profiles occupy 12 native columns, the back 14, centered in 24×36 frames with anchor `[12, 34]`. Fixed band boundaries preserve the head, shoulder, waist, hem, calves and boot heights. `export.json` records all source bounds and native registration.

An explicit bun-highlight landmark uses the hair ramp, keeping it recolorable. Profile eye cleanup registers a single dark pupil at row 9 and a blue iris at row 10; the back has no eye landmarks. The palette builder applies sage/green-eye and plum/hazel-eye variants to the same pixel layout. Skin, boots, outlines, alpha and shading positions stay fixed across palettes.

`PROFILE_JAW_CLEANUP` replaces the three outline pixels beneath each profile's iris with existing skin base/shadow shades. The exported recipe records these native landmarks. This removes the open-mouth reading without changing eyes, silhouette or the head's registration. Palette variants and the gardener inherit these source pixels.

Four non-overlapping appearance layers per direction reconstruct each native sprite. These support later pose preparation; they do not implement a walk cycle. Existing frame approval statuses survive rebuilding; new frames default to draft.
