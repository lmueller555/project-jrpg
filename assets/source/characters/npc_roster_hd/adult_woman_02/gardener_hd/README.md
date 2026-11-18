# Sanctuary gardener: native action drawings

These 98 complete pose drawings migrate the sage civilian (`adult_woman_02`) into the existing sanctuary gardener routine. Each exported body is native 96×96 RGBA, representing the unchanged 48×48 logical action canvas. Canonical adult head/face/hair, skin, sage garment, belt and brown footwear identify the character throughout.

## Construction and reproduction

`drawings.json` contains explicit final-coordinate polygon and line records for each flattened pose. `export.py` only rasterizes these records and stamps the character’s matching approved directional head; it does not derive joint motion, rotate bitmap limbs, enlarge a legacy body, or warp an idle. The ordinary rest pose reuses the complete current native idle without scaling. Compatible same-character skirt and boot contour guides from the approved directional walking poses supply carrying contact/passing drawings. New action sleeves, forearms, fingers, torso bends and reach silhouettes are explicit native contours, not the old gardener arm-line recipe.

Run from any directory:

```sh
python assets/source/characters/npc_roster_hd/adult_woman_02/gardener_hd/export.py .
```

The positional argument is the repository root. Inputs are the four canonical `adult_woman_02` idles and the legacy gardener manifest. `provenance.json` records their hashes.

## Units, behavior and props

The top-level density is 2. Body output is 96×96 artwork pixels; `action_canvas`, `body_offset`, `draw_anchor`, `foot_anchor`, all grips and all bucket metadata remain **logical world pixels**. The 98 pose names, 18 sequences, durations, effects, water capacity and draw order retain the old manifest contract. The existing bucket records are copied unchanged, with `bucket_bank` identifying their original asset directory. This is an actor appearance migration, not a pail/well redesign.

Front gestures expose the hands over the body. Rear reaches correctly put the hands and held pail in front of the actor in world depth, thus behind the torso from the camera; some intermediate drawings are almost entirely occluded. The source preserves that physical overlap rather than painting hidden fingers through the back. Natural reach takes priority over exact historical hand coordinates. The intentionally unchanged old grip can be a few native pixels from the authored fingers.

## Validation boundary

Native body dimensions, hard alpha, unclipped silhouette, input hashes, pose-set parity, logical offsets, all grips/orders and sequence equality are checked. Preview sheets show the exact retained pail attached to each new body, and native and slow sequence GIFs were reviewed as motion/occlusion evidence. Final acceptance additionally requires the actual integrated gameplay renderer, full well cycle, blocked movement and return-to-rest tests. A standalone body proof does not replace those scene checks.
