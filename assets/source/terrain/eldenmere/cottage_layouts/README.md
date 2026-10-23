# Sized cottage interior layouts — approved

Three approved furnished interior arrangements use the user-selected 10×10, 13×10 and 16×10 floor envelopes. The size templates and arrangements are approved; named household assignments remain future work. They retain larger separate room maps, the 24px grid and original 24×36 Caelan. The older 10×8 showroom remains unchanged.

This milestone assembles approved native tiles, furnishings, hearth frames and exterior sprites. It creates no new painted art and never resizes source sprites. `recipe.json` retains explicit room dimensions, fixture placements, furniture source references, character positions, interaction approaches and the wide cottage's cutaway divider. Furniture and character scale is identical in every room.

Compact: one sleeping/living room, a short cooking corner, narrow pantry and one dining chair. The basin and larger cupboard are omitted to control density. Standard: sleeping/storage to the west, cooking to the east and a two-seat dining group. Wide: a cutaway plaster/timber divider separates a sleeping/storage nook from the kitchen and three-seat family dining area. It uses one bed; this review does not assign a household size or invent extra bedrooms.

## Exterior alignment

The 3×3, 4×3 and 5×3 exterior ground rectangles correspond to the user-selected floor rectangles of 240×240, 312×240 and 384×240. Walls and void add rendering space, producing room images of 288×336, 360×336 and 432×336. Floor depth stays ten tiles. These sizes replace the earlier smaller review; furniture counts and native sprite sizes remain unchanged. Door centers are projected proportionally from exterior ground coordinates and snapped to two native pixels, giving interior south-entry centers x=102,178,252 with at most one pixel of registration error. The 24px entry may straddle floor tiles; the front cap is cleared exactly at its bounds.

Chimney centers derive from the approved base chimney position and each exterior's documented ±24px assembly offset. They land at x=204,278,350 inside the room images, within half a pixel of their ideal proportional positions. The hearth's narrow chimney therefore stays on the same side and relative horizontal position as its exterior flue. All hearths stand on the same floor plane with a 44×20 base. Rear windows are separate from the front windows omitted by the cutaway south wall; no north door is added. Supports and windows are placed to stay clear of each other and the hearth.

The wide room divider reuses the approved west-side wall's native 12×24 strip six times, forming a 12×144 cutaway partition. It uses the existing floor envelope and leaves a 96px opening at its south end. No new texture or automatic extra floor area is introduced.

## Access checks

Each furnishing retains its approved suggested floor rectangle, translated into room coordinates; wall shelves do not block the floor. A conservative **24×12 floor probe** tests character standing space on a two-pixel lattice. Flood fill starts immediately inside the south entry and must reach every recorded furniture approach and Caelan's foot anchor. It accounts for all furniture, the hearth and the partition. This is layout validation and planning data, not implemented engine collision or interaction.

The floor probe can traverse each entire required route, so the check covers doorway clearances rather than only point paths. It is a minimum access test, not a claim that every aisle is 48px wide. The compact keeps a combined living/sleeping arrangement; the larger rooms provide broader separation between activities. Chair approaches may be from the side where seating is tucked under the table. Furniture density and arrangements are approved.

## Animation and exports

The approved four fire poses retain 300ms timing. Daylight preserves the nine 600ms strengths but projects the existing window's glass mask at each room's rear windows. Soft floor firelight follows the hearth's new position with the same fixed two-band mask and color strengths. The combined loop remains 36×300ms =10.8 seconds. Draw furniture, the hearth and Caelan by their floor-foot baseline so near objects can occlude distant ones naturally. All original sprites and source files remain unchanged.

Each room exports native structure layers, placement/source metadata, suggested blockers, valid floor-probe centers, lighting masks, 36 native scene frames, a 4× still and a 4× GIF. The synchronized comparison places the matching static exterior above each interior, all at the **same 3× nearest-neighbor scale**. Labels are outside room images. The comparison preserves room size differences instead of fitting each room to an equal-width thumbnail.

Build: `PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/project-jrpg/bin/python tools/build_eldenmere_cottage_layouts.py`.

Check with the same interpreter and `tools/test_eldenmere_cottage_layouts.py`. The builder writes only the new layout pack. The three layout designs are approved. Palette-specific household dressing, engine collision and room transitions remain future work.
