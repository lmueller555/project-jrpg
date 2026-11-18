# Picker native activity candidate

Candidate only, runtime activation false. No controller or shared loader edited.

47 complete 80×88 native drawings at 2 pixels/world pixel. Standing root40,76; exact canonical travel padding[16,7] puts neutral sole69 at native76 (exclusive alpha bound77); seated root40,88. Rust-shirt adult_man_02 identity remains exact: native canonical protected head, existing palette and shirt/belt details. No apple baked into character.

## Authorship and sources

`assets/source/characters/regional_npc_hd/regional_picker/actions_hd/author.py` is the native drawing source; adjacent masters are authoritative complete drawings. Explicit whole-pose contour JSON copies the accepted adult_man_02 front/back/right native-v1 walk K definitions as same-phase motion guides. Arms and garment resolution are new hand-plotted pixel contours, not a joint solver or transformed limb raster. Each complete drawing renders before technical export. Carry front/back body/legs follow that named character's accepted gait. Protected head is the original directional top28 pixels, registered to the authored bob. Stationary work retains only the unchanged planted lower-body support crop x16..32/y46..71, excluding original idle hands. Reach, admire, lower, sort and seated rest have explicit independently specified complete upper/body poses. Sort bends both knees with fixed soles and lowers the head coherently.

Canonical left idle is byte-identical to the reflected right idle. Left carry uses reflected complete right drawings with half-cycle phase reorder, not runtime limb mirroring. Both step contacts differ in actual lower pixels in all directions. Source preserves rust palette, short dark tousled hair, collar and belt; no new person substituted.

## Review findings

Reviewed native/enlarged contact proofs. Removed accidental old idle hands at hips from stationary source crop; occluded rear gripping hands; redrew set-down forearm inward toward fruit rather than extending reach unnaturally. Both profile directions face correctly and contain two-step gait with opposite support. Body canvas has ample margin and no clipping. Rest is intentionally a single still seated pose, not artificially breathing legs.

`prop_context_2x.png` is a prop-placement diagnostic, NOT a gameplay screenshot. It overlays original apple pixels at existing controller hand coordinates without changing ownership. Carry apple is between the front hands, below the side hand, and naturally occluded from back. Admire/lower use existing high-to-low prop trajectory. Reach apple is at face height by existing `(2,-22)` offset; foreground grip reaches its lower edge. Sort keeps original `(0,-7)` position until controller contact rather than artificially forcing the sprite to the basket. Actual scene review by integrating lane remains necessary, particularly high reach occlusion and sort-to-basket deposit.

## Technical evidence

`tests.log`: 7/7 scoped tests pass, checking dormant flag/scale/anchors, exact native-source export, two-step lower-pixel distinction, 680ms cadence, profile identity symmetry, required sequence inventory. `measurements.json` records per-frame alpha bounds, hashes and unique count. These are technical checks, not substitutes for visual acceptance. `contact_native.png`, `contact_2x.png`, per-sequence4x GIFs and prop context accompany source.

Rebuild native source: `python assets/source/characters/regional_npc_hd/regional_picker/actions_hd/author.py`.
Export: `python tools/build_regional_picker_actions_hd.py`.
Nonwriting verification: `python tools/build_regional_picker_actions_hd.py --check`. Checks encoded outputs in memory, fails on missing/mismatched output, never repairs. Tests also compare tree bytes/mtimes before/after and rerender author in a temporary directory byte-exactly. Ground test compares each accepted gait support contour with exact padding, preserving original one-pixel gait sole variation rather than forcing it flat.

Test: `python -m unittest discover -s tests -p test_regional_picker_native_actions.py -v`.

Integration owner maps action keys without program/state/collision changes. Presentation-only lower_front must use existing elapsed/duration progress. Carry cycles8×85ms preserve legacy680ms. Reach and sort4×450ms match1.8s; lower4×250ms matches1s. Admire2×650ms maintains legacy idle beat; rest is static with separate anchor. No native activity selector should alter the three apples, portable owner, pickup/put contact time, basket quantity, path, dialogue, or durable state.
