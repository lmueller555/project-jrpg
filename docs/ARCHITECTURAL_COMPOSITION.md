# Architectural composition and seamless transitions

**Status:** Production contract (2026-10-15). Applies to towns, interiors, dungeon rooms, and structures across Project JRPG.

## Space and coordinate rules
- Maps retain independent 16-unit gameplay/collision cells during migration. The presentation renderer resolves each cell to 32 native pixels. Never mutate a map to make a sprite fit.
- The single source of truth for walkability and triggers is map JSON. Architecture draws a *visual* skin; it may extend beyond collision as deliberately authored relief.
- Use world-space pixel coordinates and camera translation only at the blit boundary; do not define assets in camera-space.
- Door anchors derive from actual transition-object rectangles. A larger decorative surround extends evenly around an opening without changing the opening's gameplay footprint.
- Window instances belong to authored/derived wall bays. A tall window in a shallow north collision wall is an *alcove* and must include authored wall backing behind the extension. Do not leave it floating on exposed floor.

## Transition art standards
- Seamless floor variants must share compatible borders. Across a continuous material, tile edges must match in palette, grout width, noise density and light direction.
- Separate interior fills from boundaries: baseboard/wall-foot, straight edge, inside corner, outside corner, doorway jamb, sill, threshold, pillar joint.
- Architectural masonry uses explicit edge/corner modules and oriented adjacency, not arbitrary 47-blob terrain masks. Organic material transitions may use the established 47-tile scheme.
- Stable per-coordinate variant selection is acceptable only when all variants share seamless edges. Prefer seeded map-stable hashes or locked art overrides to random-per-frame noise.
- Never solve a missing transition with a dark rectangle, random overlay, canvas crop, or smoothing.
- Lighting is a separate transparent pass. A window emits its light from its *instance position*, not duplicated hardcoded coordinates. Validate alpha at both the sprite and composited-frame level.
- Reusable assets require semantic IDs, tested anchors, native pixel-grid sizes and documented overhang/footprints.

## Validation gates
1. Structural topology test: floors, walls, corners, opening containment and exit alignment.
2. Asset test: PNG decode, bounds, alpha, compatible floor seams and clean silhouettes.
3. Camera test: same world positions at different camera offsets, with no drifting windows/doors/lights.
4. Pygame capture at 640×448 plus integer-scale screenshot: human review of wall-floor junctions, door clearance, occlusion, opaque lighting artifacts, repeating seams.
5. Gameplay regression: unchanged collision, character spawn, exit trigger and outdoor presentation.

## Adoption
`engine/architecture.py` is the initial pure-data resolver; `engine/sanctuary_visuals.py` is the reference implementation. Future locations should use the same resolver patterns and explicit material/anchor definitions. Do not copy sanctuary pixel offsets into unrelated maps. Later PRs can extend the schema with authored window/opening lists and configurable wall face/corner variants as the corresponding PNG art becomes available.
