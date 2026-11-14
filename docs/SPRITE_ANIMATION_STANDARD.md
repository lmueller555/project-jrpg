# Sprite and animation standard

This is the authoritative authoring guide for character and NPC sprites and
animations: appearances, directional idles, walks, runs, combat and scene poses,
export recipes, and visual review. Its walking workflow consolidates the lessons
from Iselin's four approved cycles. Read it before creating or revising artwork,
builders, or animation tests.

This standard replaces conflicting general advice in older character recipes,
tool descriptions and review notes. Those files retain asset-specific facts,
commands and historical evidence; they do not prescribe new construction methods.
Existing approved assets need no automatic rebuild or conversion. Apply these
rules to the work being requested. Explicit user direction takes precedence.

For actions involving objects, also follow the
[character–object interaction standard](OBJECT_INTERACTION_STANDARD.md) for
staging, ownership, transfer cues and lifecycle, and
[personal-prop visibility](PERSONAL_PROPS.md) for equipment visibility. This guide
owns sprite construction and motion quality; those companions own interaction
behavior. A walk's limb amplitudes and timing are not rules for every combat pose.
The limb examples below describe a biped. For creatures with different anatomy,
plan their actual limb chains, support pattern and silhouette rather than forcing
a human two-arm/two-leg gait onto them.

## Working order

1. Inspect the approved art and runtime format; record design, sides, density,
   anchors, body landmarks, frame budget and cycle duration.
2. Establish directional idles and inspect them at cast scale.
3. Draw contact/passing keys for one direction and inspect all limb paths before
   spending effort on transitions. A readable profile is useful for diagnosing
   near/far movement; the requested direction still determines the work scope.
4. Draw small batches of in-betweens against those keys and the same proportion
   reference. Export and inspect each batch at native resolution.
5. Assemble chronological poses, register by body landmarks, and inspect both
   half-cycles, batch joins and the loop seam. Correct the diagnosed defect.
6. Produce normal/slow previews and a numbered sheet; run the appropriate checks.
7. Carry the successful gait to other directions with their own approved
   appearance and occlusion. Check the complete directional set together.
8. Record the current revision, review outcome and requested merge boundary.
   Validate actual travel when runtime integration is part of the task.

Do not generate a larger batch to compensate for failing key poses. These are
internal quality checks, not extra user approval steps; ask for review at the
boundary the user requested.

## 1. Establish the character before animating

Use approved appearance references, not a fresh interpretation in every frame.
Create a character sheet or source recipe containing:

- The approved design, palette, silhouette and front/left/right/rear idles.
- Head width and height, neck length, shoulder width, torso length, waist,
  coat/garment length and limb proportions. Record stable landmarks in artwork
  coordinates, with a side-by-side comparison against the existing cast.
- Hair construction, face features and each asymmetric costume element, named
  by **anatomical left/right**, not just the side of the image.
- Frame dimensions, artwork density, logical world size, draw and ground
  anchors, collision footprint, frame budget and intended playback cadence.
- Source paths, generation/edit instructions, approval scope and export recipe.

Match the cast's pixel-art style: a readable dark/black exterior outline,
consistent outline weight, coherent material shading and clear gaps between
limbs. Keep small faces and costume details readable against bright and dark
scenery. Do not outline every internal feature with equally heavy black lines.
Check outline continuity through motion; a good idle does not guarantee a good
walking silhouette. Keep a consistent palette rather than changing hair, skin,
clothing or outline colors between frames.

Build all required directional idles before their walks. Each direction needs a
specific appearance reference. Profiles must retain the face, coat, mantle and
hair detail instead of becoming reduced-detail silhouettes.

### Artwork pixels, world pixels and display pixels

These are separate units. Record which unit every measurement uses. More source
pixels do not require a taller character, a larger collision box or a larger
world-space stride.

Iselin is a worked example, not a universal size requirement:

| Property | Approved Iselin value |
| --- | --- |
| Exported artwork frame | 42×72 RGBA |
| Artwork density | 2 artwork pixels per world pixel |
| Logical frame | 21×36 world pixels |
| Draw anchor | [21,60] artwork / [10.5,30] world |
| Ground/foot anchor | [21,68] artwork / [10.5,34] world |
| Collision probe | 8×4 world pixels |
| Walk | 16 frames × 35 ms = 560 ms per full two-step cycle |

The established detailed renderer preserves higher-resolution idle and walk
artwork at ordinary party scale. Resizing it to the logical fallback discards detail;
enlarging that fallback later cannot recover it. Validate the intended rendering
path and target window scale. Iselin's walk manifests are registered on her
reusable actor; the full regent character/story replacement remains separate
from that rendering integration.

## 2. Plan the gait before drawing in-betweens

A full walking cycle contains two steps and returns to the same limb phase.
Choose frame count and total duration together. Extra frames subdivide movement;
they do not automatically make the walk slower or smoother. Iselin's 16×35 ms
cycle and older 4×140 ms cycles both last 560 ms. Existing approved cadences
remain character-specific; do not silently retime the cast.

Draw and inspect contact and passing keys first. Add down/recoil and up/recovery
poses, then intermediate drawings. This is a useful 16-frame planning template;
the actual approved motion, rather than the file number, determines each phase:

| Frame | Phase | Main action |
| --- | --- | --- |
| 1 | Right-foot contact | Right leg leads, left arm leads; opposite limbs trail. |
| 3 | Down/recoil | Weight settles onto the right support leg; left foot releases. |
| 5 | Passing | Left swing leg passes the support leg; both arms pass through their middle range. |
| 7 | Up/recovery | Left foot approaches its next contact; right foot finishes support. |
| 9 | Left-foot contact | Left leg leads, right arm leads; identities exchange. |
| 11 | Down/recoil | Weight settles onto the left support leg; right foot releases. |
| 13 | Passing | Right swing leg passes the support leg. |
| 15 | Up/recovery | Right foot approaches contact; left foot finishes support. |
| 16 → 1 | Loop seam | Continue into contact without a pose reset or repeated endpoint. |

Even-numbered frames bridge these keys. Do not fill them with almost identical
extended-leg poses and then jump to the next phase. Do not assume an image
generator's column order is a valid chronological cycle: inspect and label it.

### Arm and leg coupling

Each arm counters the **same-side leg**: left arm forward with left leg back,
and right arm back with right leg forward; reverse together on the next step.
Thus left arm and right leg move forward together. Track all four limbs by
anatomical identity throughout the cycle, including when hidden.

The desired expressive swing can approach roughly 45° forward and backward
in the sagittal plane, relative to a relaxed vertical limb. Treat that as an
art-direction target, not a requirement to draw straight limbs or force every
projected angle to 45°. Bend knees and elbows naturally. Front/rear views
foreshorten this motion in depth; they must not kick sideways to imitate a
profile's screen-space reach. Shorter foot reach is preferable to an exaggerated
kick followed by a landing snap. Natural anatomy takes priority over a numeric
angle, exact contact coordinate or old test.

## 3. Draw complete, coherent frames

For new or revised walks, author each pose as a complete character drawing with
its near/far overlaps resolved. Export flattened RGBA frames. Do not manufacture
the cycle by rotating, sliding or stretching detached arms and legs around an
unchanging body, or by warping a flattened idle. Adding more frames to a limb
rig does not fix parked far limbs, duplicate hands or incorrect anatomy.

Use one approved proportion reference and the same landmark grid for every
strip. Small batches of complete drawings can help control motion, but every
batch must use the same body scale and phase plan. Review batch boundaries as
carefully as transitions within a strip. Pixel interpolation, cross-fading and
duplicate poses are not substitutes for drawn in-betweens.

### Reusable drawing/edit brief

Supply the actual reference images and a short phase table with the request.
Replace the bracketed fields; vague requests for a "smooth walk" leave too much
unspecified. For a repair, include adjacent good frames, not just the bad extreme.

> Draw [count] complete [direction]-facing character poses in [layout], in the
> phase order [listed contacts, passing poses and transitions]. Use [approved
> directional idle] for appearance and [approved keys] for gait. Preserve
> [head/neck/torso proportions and landmark grid], [anatomical costume sides],
> [palette and outline style]. Track each near/far arm and leg through the
> listed phases with natural occlusion. Keep [frame size/density] and
> [crown/neck/belt reference positions]. Draw [specified foot progression],
> without a held extreme followed by a reset. Use complete unified drawings,
> transparent background and clear cell separation. No extra limbs, sideways
> depth kicks, changing body scale or detached old pose pixels. For this repair,
> change [specific defect and frames] and preserve [accepted region/motion].

Keep image generation responsible for authored redraws; technical export handles
crop, alpha, uniform sampling, registration and documented pixel preservation.
Do not hide a new procedural anatomy/limb generator inside the exporter.

### Near/far limbs and occlusion

Inspect the near arm, far arm, near leg and far leg separately. Both pairs must
advance through the gait; animating only the camera-facing side is insufficient.
Trace shoulder → elbow → hand and hip → knee → ankle for each pose. There must
be exactly one anatomical chain for each limb, with coherent attachment points.

A far hand or leg can legitimately disappear behind the torso, coat or near
limb. Record the hidden phase and make its next appearance consistent with the
continuing swing. Do not draw it through the body to prove it is moving. Remove
the original idle hand/arm when redrawing its pose: leaving both is how a third
arm appears. Likewise, remove obsolete boots, coat fragments and outlines.

### Direction changes and asymmetry

| View | Anatomical left appears on | Anatomical right appears on |
| --- | --- | --- |
| Front | Viewer right | Viewer left |
| Rear | Viewer left | Viewer right |
| Left-facing profile | Near side | Far side |
| Right-facing profile | Far side | Near side |

An approved opposite-side gait may supply reflected **motion guides**. Redraw
the new direction's face, clothing and hair from its approved idle; do not flip
the finished asymmetric costume and call it complete. Document any deliberate
reuse of already approved pose pixels. Iselin's left walk preserves reflected
approved lower-leg movement while using new left-specific upper artwork.

For Iselin, the mantle is on anatomical right and the braid runs forward over
anatomical left. Her rear view shows the braid root/bend, not a newly invented
central ponytail. Keep hairstyle identity intact while adding sway.

Hair, braid tails, mantle and coat may lag the body motion slightly. Draw modest
secondary motion that follows the gait and loops smoothly. Avoid abrupt hair
length, volume or silhouette changes that read as character redesigns.

## 4. Make feet progress continuously

Separate **stance** from **swing**. During stance, the support foot progresses
backward relative to the travelling body. During swing, the other foot lifts,
passes, reaches and settles into contact. Use a consistent toe/heel landmark;
a bounding-box center can jump when the boot rotates without the foot actually
moving that far.

Inspect each leg over an entire half-cycle and through the handoff. Watch for:

- An extended foot wiggling in place for several frames, then teleporting behind.
- Excessive lift or reach immediately followed by a drop into contact.
- Abrupt reversals, horizontal track changes, flashing soles or foot identity swaps.
- Both legs becoming static while the arms continue, or changing direction at
  unrelated times. Allow natural double support during walking.

Record foot contact/release phases and per-frame landmarks. Compare neighboring
displacements and loop-seam displacement; inspect sudden outliers visually.
Ease the approach to contact and draw the missing passing/recovery poses instead
of reordering unrelated extremes or shortening a frame to hide a snap.

Iselin's rear boot once dropped about nine artwork pixels from frame 4 to 5.
The correction reduced lift and divided the return into smaller drawn changes;
the accepted revision has no adjacent vertical change above three artwork pixels.
That is a regression bound for this asset, not a universal speed limit. Front/rear
screen-space boot height also represents depth, so measure the intended motion.

An in-place preview does not prove world-ground foot locking. When integrating
travel, compare stance-foot motion against actor displacement at the intended
world speed: support-foot movement relative to the actor should approximately
cancel actor travel. Check actual scenery playback for sliding and skating.
Fix cadence, stride or pose construction rather than moving collision geometry
to chase the artwork. A run additionally needs its own weight/flight phases;
simply accelerating a walk does not establish a convincing run.

## 5. Register the body; author the bob

Keep scale and pose displacement separate. Use a common pixel density and stable
body landmarks such as crown, head center, neck, shoulder line and belt/pelvis.
Preserve head size, neck length and torso proportions across the complete cycle.
Use multiple landmarks: a fixed crown alone can conceal a stretching torso.

**Do not normalize each pose or strip to its occupied height, or align the body
by the lowest opaque boot pixel.** A lifted foot, bent knee, hair tip or longer
stride changes those bounds. Separate strips normalized that way can have
different body scales even though every output canvas has identical dimensions.

If source canvas density differs, use audited body landmarks to derive a uniform
whole-drawing scale and registration. Record the landmarks, crop, scale and
origin. Never independently stretch horizontal and vertical axes or resize
individual limbs to make landmarks meet. If several body proportions still
disagree, redraw the source rather than repeatedly compensating during export.

Author a small, periodic vertical bob tied to weight transfer. At Iselin's
42×72 density, a total excursion around 1–2 artwork pixels is a useful initial
range, not a requirement for every character or gait. Keep the head, neck,
shoulders and torso coherent; the legs accommodate weight transfer naturally.
Keep support-foot contact grounded rather than translating the whole character
and its planted boots up and down. Do not add another runtime bob to artwork
that already includes one.

Iselin's accepted rear crown positions are
`3,3,2,2,3,4,4,3,3,3,2,2,3,4,4,3`: two gentle excursions per full cycle,
no neighboring jump above one artwork pixel, including frame 16 → 1.
The earlier four-pixel down/up impulses were export/proportion defects.
Check exported head and belt pixels, not just the bob array in the recipe.

Keep the character's declared draw/ground anchors and world position consistent
across directions, idle transitions and poses. The ground anchor is a logical
registration reference; it is not recalculated from whichever foot is lowest.
Do not change collision size as an incidental result of a larger art canvas.

## 6. Correct one defect while protecting accepted work

First identify the failing frames and anatomical chain. Preserve snapshots of
the accepted parts before editing. Ask image generation to redraw complete poses
with the specific defect corrected, using the approved appearance and motion
references. Do not request unrelated redesigns during a foot correction.

A documented regional edit may restore accepted pixels outside the repair area
after a complete drawing is redrawn. This protects approved arms, boots or body
detail against incidental generation drift; it is not a detached-limb animation
system. Do not rotate, translate or stretch an isolated leg to manufacture poses.
Save the complete generated master, protected snapshot, repair window and hashes.

Inspect the repair boundary on every frame. Check knee continuity, cloth/skin
joins, duplicated outlines, stale boots and floating coat hems. A protected
upper region can preserve an existing body-height defect; passing a pixel-equality
test only proves preservation. Expand the scoped redraw when the actual defect
crosses the boundary, and document which previously protected pixels changed.

## 7. Export reproducibly

Retain original sources unchanged under `assets/source/`, plus the recipe,
source hashes, selected cells/order, landmark coordinates, scales, origins,
palette/alpha settings, protected regions and approval state. Keep superseded
attempts and previews labeled as history. Record which revision is current.

Export to the character's existing asset layout: complete frame PNGs, native
spritesheet, and metadata containing frame rectangles, individual durations,
loop behavior, density and anchors. Use uniform nearest-neighbor sampling for
pixel art and hard transparency where the existing character format requires
it. Remove background fringe without destroying slim fingers, braid strands,
boot gaps or the outline. Inspect component extraction; the largest connected
component is not automatically the whole valid drawing.

Rebuilds must preserve approval state and leave approved references unchanged.
Do not silently regenerate the idle, other directions, portrait or costume while
exporting one walk. Keep asset approval, merge state and runtime activation
distinct; a merged animation pack does not imply that actor selection uses it.

GIF delays are quantized to centiseconds. For 35 ms playback, alternating
30/40 ms delays reproduces the average cadence and total duration. Label slow
previews clearly and verify the actual saved GIF timing. Review PNGs remain the
reference for exact colors, alpha and fine detail.

## 8. Review at three levels before declaring completion

1. **Drawings:** numbered native frame sheet with constant nearest-neighbor
   enlargement. Trace all limbs; inspect identity, outlines, face, costume sides,
   hair, body landmarks, feet and edit seams. Include last → first.
2. **Motion:** normal-speed loop alongside half-speed playback and native-size
   examples. Compare with the approved idle and cast scale. Inspect contact,
   passing and weight transfer; more unique files alone do not establish motion.
3. **Game rendering when integrating:** travel against actual scenery at the
   intended speed and detail density, with relevant light/dark backgrounds,
   camera scale, idle/walk/direction transitions and depth occlusion. Use temporary
   saves or nonpersistent fixtures. A standalone asset review may defer this
   integration check, but must say so.

Use focused automated checks for the actual defect and export contract:
dimensions, alpha, unclipped bounds, frame ordering/count and timing, sheet
reconstruction, loading, landmark continuity, loop seam, expected contact phases,
and exact preservation of explicitly protected artwork. Where a motion landmark
is occluded, annotate its phase or inspect it manually rather than measuring an
unrelated visible component. Do not add anatomy-distorting tests to satisfy
arbitrary joint angles or exact hand positions. Count/uniqueness checks alone
cannot certify a gait, and passing tests never replaces viewing the frames.

### Completion checklist

- [ ] Approved design and direction references; explicit anatomical sides.
- [ ] Coherent full-body drawings; all four limb paths account for occlusion.
- [ ] Continuous support, passing and contact; no parked-foot snap or extra limbs.
- [ ] Stable head/torso proportions and landmark registration; deliberate modest bob.
- [ ] Correct directional costume/hair, restrained secondary motion, readable outlines.
- [ ] Clean repair boundaries, unclipped pixels and smooth final → first transition.
- [ ] Reproducible sources, manifests, timing, anchors and current revision/status.
- [ ] Normal/slow preview, numbered sheet and scale comparison visually inspected.
- [ ] Appropriate checks pass; runtime integration validated or explicitly deferred.
- [ ] Requested review/merge boundary respected; describe remaining limitations plainly.

## 9. Diagnose before regenerating

| Observed defect | Likely cause | Targeted correction |
| --- | --- | --- |
| Near side walks; far side stays parked | Only the visible-side chain was planned | Trace all four limbs through contact/passing and redraw hidden/reappearing phases. |
| Three arms, hands or boots | Old pose pixels survived a replacement | Remove the obsolete silhouette and resolve overlaps in the complete drawing. |
| Foot wiggles ahead, then jumps behind | Repeated extreme poses; missing progression | Rebuild stance/passing in-betweens and verify landmark progression. |
| High kick followed by a sharp landing | Excessive reach/lift and insufficient recovery | Reduce excursion and distribute the approach to contact across drawings. |
| Character grows/shrinks or twitches | Source proportion drift; foot/height-based normalization | Audit head, neck, belt and shoulders; redraw inconsistent proportions and register by body landmarks. |
| Floating silver hem or broken knee | Partial edit restored stale pixels at its seam | Redraw a coherent boundary and protect artwork beyond it. |
| Opposite direction swaps braid/mantle | Finished asymmetric sprite was mirrored | Use mirrored motion only as a guide and redraw direction-specific appearance. |
| Body looks fine enlarged but skates in game | Cadence/stride mismatch or wrong world/art units | Compare stance with actor travel and verify density/anchor use. |
| First frame pops after the last | Endpoints and secondary motion were reviewed separately | Inspect the loop seam as an ordinary adjacent pair and draw its missing transition. |

## Implementation references (examples, not competing standards)

- [Iselin front walk](reviews/iselin_front_walk/README.md): complete-frame source
  and the 16-frame cadence.
- [Right walk leg correction](reviews/iselin_right_walk_redrawn/LEG_REVISION.md):
  preserve accepted arms while repairing foot progression.
- [Left walk](reviews/iselin_left_walk_redrawn/README.md): reuse approved motion
  with direction-specific costume and braid motion.
- [Rear walk, final body revision](reviews/iselin_back_walk/README.md#body-stability-correction-revision-3-current):
  smaller boot lift, body-landmark registration, controlled bob and seam cleanup.
- [Iselin detailed idle rendering](reviews/iselin_first_assets/IMPLEMENTED.md):
  artwork/world density and production occlusion.
- [Iselin runtime walking](reviews/iselin_walk_integration/README.md): shared
  logical/detail timing, navigation, stopping, turning and real foliage occlusion.
- [Asset tool catalogue](../tools/README.md): commands and local implementation
  details, including legacy builders retained for reproducibility.
