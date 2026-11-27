# Sprite and animation standard

This is the authoritative authoring guide for character and NPC sprites and
animations: appearances, directional idles, walks, runs, combat and scene poses,
export recipes, and visual review. Its gait workflow consolidates the lessons
from Iselin's approved walks and the cinematic running reviews. Read it before
creating or revising artwork, builders, or animation tests.

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

| Property | Approved current Iselin value |
| --- | --- |
| Exported artwork frame | 24×36 RGBA |
| Artwork density | 1 artwork pixel per world pixel |
| Logical frame | 24×36 world pixels |
| Draw anchor | [12,30] artwork/world |
| Ground/foot anchor | [12,34] artwork/world |
| Collision probe | 8×4 world pixels |
| Walk | 16 frames × 35 ms = 560 ms per full two-step cycle |

The approved native idle and walk PNGs feed one ordinary sheet-based actor.
They do not use detailed-image overrides or runtime downsampling. Display and
cinematic camera enlargement remain separate from source artwork density:
native-derived scene canvases preserve the native pixel clusters and costume.
The separately approved detailed gate performance is described in section 10;
it does not change the ordinary actor's native art or collision.
Validate the intended drawing path and target window scale, together with
foreground depth and seated/aerial registration.

Iselin's superseded detailed bank and prototype studies were deleted after the
native replacement was approved. They are no longer construction or rendering
requirements. The individual native approval reviews preserve their original
scope and captures; the integration review records current gameplay consumers.

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

## 2A. Construct running as its own performance

A run needs support, compression, propulsion and flight; accelerating a walk
does not supply those actions. Plan a full two-step cycle with anatomical limb
identities, contact/release cues and the intended travel speed before drawing
intermediates. Establish readable keys for each half-cycle:

| Phase | Required movement |
| --- | --- |
| Contact | The advancing foot approaches the ground without a last-frame drop; the other leg finishes recovery. |
| Compression | The support knee accepts weight and the pelvis settles; the arms continue through their swing. |
| Push-off | The support leg extends behind and the other knee advances; the shoulders counter the pelvis. |
| Flight and exchange | Both feet briefly clear the ground; the recovering leg folds and passes before extending toward the next contact. |
| Opposite contact | The anatomical roles exchange continuously, without a held extreme or a pose reset. |

Flight duration, knee lift, torso lean and arm amplitude depend on effort,
equipment and character. Keep a coherent shoulder–elbow–hand and
hip–knee–ankle chain even when an overlapping body part hides part of it.
Front and rear views express the swing partly through depth and foreshortening;
do not substitute sideways kicks. Avoid a fixed upper-body carry over rapidly
cycling legs. Natural shoulder and pelvic counterrotation, a small controlled
head response and weight transfer should connect the body without changing its
proportions. Registration preserves scale and identity; it must not erase the
authored action by pinning every body landmark to an unchanging position.

For an initial two-step phase chart, place opposing arm extremes around the two
contacts and neutral arm passes around the quarter- and three-quarter-cycle
positions. Adjust that relationship for the actual carry and action, then trace
the wrist relative to the shoulder and waist across the entire cycle. A key sheet
can exchange the arms too early and hold the same apex through several labeled
phases. File numbers and phase captions do not prove the drawn motion matches
the chart. Simple anatomical landmark guides may constrain whole-frame image
authoring; those guides must never become a procedural limb-animation exporter.
Compare actual drawn hands and feet with the guide before accepting a batch.
If intermediates keep a held extreme despite different captions, diagnose the
painted positions relative to the neck, waist or costume fasteners. Repair the
missing positions with explicit anatomical/costume targets; another phase label
or a more detailed prompt is not evidence that the drawing followed it.
If every new pose returns to the same contact despite correct guides, change
the visual reference hierarchy: use the correct adjacent/opposite-contact pose
as the primary motion reference and cropped face/costume details for identity.
A strong full-body appearance reference can inadvertently keep supplying its
original limb arrangement. Recheck actual anatomy before authoring more frames.
When a wide-interval in-between repeatedly lands at the wrong phase, establish
and inspect its midpoint first, then subdivide the shorter accepted intervals.
Use the closest actual drawings as motion bounds. Do not keep requesting small
percentage changes against two distant extremes while accepting identical
intermediate poses. Verify each new interval before densifying it further.
Establish the actual same-character contacts, passing poses and their midpoints
before those subdivisions. Another character can supply a motion guide, but a
full painted body reference can transfer its torso/leg proportions as well as
its pose. Re-establish the requested character's model first; matching the face
and costume alone does not establish anatomical continuity.

### Cadence, travel and presentation are separate choices

Record the full two-step duration, poses and exposures, ground speed, contact
phases and sound cues separately from the display frame rate. At a constant
speed, the expected distance per step is `speed × cycle_duration / 2`.
Inspect whether the drawings can plausibly cover that distance, including
support-foot locking against actual scenery. A 60 FPS cinematic can hold a
drawing for multiple display ticks; it does not require a 24-pose gait to finish
in 24 ticks. More drawings do not repair insufficient movement in the keys.

For the Veinhold reveal correction, approximately 800 ms per full cycle at
4 m/s is the scoped starting target, subject to motion review. Forty-eight
complete poses over that duration can provide a fresh drawing at every 60 Hz
tick. These values are not a universal running recipe or an acceptance test for
other characters. Approve the rough action internally before filling a larger
drawing bank. Do not satisfy a frame-count target with duplicated poses, blended
endpoints or procedural limb transformations.

Connected shots must share a coherent gait phase and travel speed. When a run
is retimed, update the moving ground, camera travel and contact Foley together.
Preserve an authored starting location independently of velocity; changing
speed must not silently relocate the group. Derive subsequent shot phases from
elapsed travel and the actual cycle rather than copying old frame indices.
Size the runtime cache or bake strategy before increasing detailed source banks.

### Weapon and shield carry

Name each equipment-bearing hand anatomically and define a safe carrying range.
Draw a clear bent-elbow arm action appropriate to the load, with the opposite
leg advancing as that arm advances. The sword hand and blade follow a connected
arm; the shield remains attached to its forearm while bobbing or tilting with
a smaller counterbalancing action. Heavy equipment can reduce excursion, but
"restrained" must not mean a straight arm parked in the same silhouette for the
whole cycle. Preserve the apparent equipment mass, grip and clearance from the
body and other runners. Rigid plate armor stays rigid while its joints move;
do not make armor ripple like cloth or redraw equipment in the wrong hand.

### Hair, braid, mantle and coat follow-through

Plan secondary motion after the body keys work. Record the attachment, free
length, baseline wind and response for each material. Keep wind consistent in
world space across camera changes and add the stride response to that baseline.
Use distinct responses rather than shifting every loose part in unison:

- Loose hair and short strands respond quickly, with continuous bends and tips.
- A heavy braid responds later, bends through its length and overshoots after
  the shoulders reverse; its root stays attached. Keep hand clearance readable,
  or resolve an intentional overlap consistently without implying an accidental
  grip.
- A mantle or shawl carries tension from its shoulder attachment through the
  fabric toward its free edge. Successive folds should describe a traveling
  wave instead of replacing one broad, held sail with another silhouette.
- Coat panels and tabards lag the hips and thighs, then settle or reverse with
  weight. Preserve their attachment, material weight and underlying anatomy.

Choose amplitude for the action and material; long hair and flowing cloth can
need substantial movement during a run. Maintain coherent volume, length and
costume construction while the silhouette changes. Do not confuse random edge
variation, disappearing hair masses or a sudden fold replacement with stronger
animation. Author these responses in complete coherent drawings. A longer
secondary-motion cycle is optional when needed to avoid an obvious repeat; it
must join cleanly and retain the same body timing.

### Running acceptance

Inspect sustained normal-speed playback against the moving environment before
using slow playback to diagnose individual transitions. Review the entry into
the shot, each limb exchange, every source-batch boundary and the loop seam.
Trace both arm pumps, leg progression, weight transfer, weapon grip, hair/braid
paths and cloth lag. Compare stable head/torso proportions without demanding
pixel-identical upper bodies. Include actual shot framing: a frontal crop may
hide the feet and make weak arms or a rigid torso especially conspicuous.

Automated checks can protect timing, contacts, export registration, ownership,
cache bounds and lifecycle. Unique PNGs, a precise 60 Hz clock or a passing
completion suite cannot certify motion quality. Record what was visually
inspected and any unresolved defects. Keep historical reviews labeled with
their revision rather than treating an earlier passing review as current proof.

## 3. Draw complete, coherent frames

For new or revised walks and runs, author each pose as a complete character
drawing with its near/far overlaps resolved. Export flattened RGBA frames. Do not manufacture
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
reuse of already approved pose pixels. Iselin's native side walks use separate
complete drawings with their own near/far mantle and braid placement.

For Iselin, the mantle is on anatomical right and the braid runs forward over
anatomical left. Her rear view shows the braid root/bend, not a newly invented
central ponytail. Keep hairstyle identity intact while adding sway.

Hair, braid tails, mantle and coat follow the gait with material-appropriate lag
and amplitude. Preserve the approved restrained response in existing native
walks; new runs follow section 2A's more active secondary-motion construction.
Avoid abrupt hair length, volume or silhouette changes that read as character
redesigns.

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

An earlier detailed Iselin study had a rear boot drop about nine artwork
pixels between adjacent frames. Reducing lift and drawing the missing return
poses corrected it. That source-specific numeric bound is historical, not a
constraint on the current native bank or other assets. Front/rear screen-space
boot height also represents depth; inspect an actual heel/toe landmark rather
than assuming every silhouette-bound change is a foot reset.

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

Author a small, periodic vertical bob tied to weight transfer when the gait
needs it. At native density, a total excursion around one world pixel is a
useful starting point, not a requirement for every character. Keep the head,
neck, shoulders and torso coherent; legs accommodate weight transfer naturally.
Keep support contact grounded rather than translating planted boots with the
whole body. Do not add a runtime bob to artwork that already includes one.

Iselin's current native walks preserve approved stationary head regions after
complete-frame authoring. The side cycles use a constant one-pixel walking
settle, while front/rear retain their registered head height. Their moving
bodies remain authored below the protected boundary. These asset-specific
choices avoid source-strip head-shape twitch; they are not a prescription to
freeze every character's upper body. Inspect the neck and garment joins and
actual weight transfer, not just the equality of protected pixels.

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

### Bind motion evidence to the painted frames

Measure the actual drawings, using reviewed anatomical landmarks or image-based
extraction whose matches were visually checked. Planned guides, phase labels
and copied target coordinates are not measurements of the finished pixels.
Bind retained measurements to the exact PNG hashes and record their crop,
registration, density and coordinate space. Changed pixels invalidate that
evidence until it is measured again. Account for occlusion and camera perspective;
do not substitute a coat edge or another limb when the intended point is hidden.
An alpha contour cannot detect internal movement over opaque clothing, such as
a braid crossing a coat. Inspect the actual RGB material in a region whose
identity was visually reviewed. Bind that region to the cropped or exported
pixel view and its crop, scale, origin and registration; an unchanged source
file can still produce a different view after an export-geometry change.
Record ambiguous or hidden material and centroid uncertainty rather than
presenting an estimated region center as an exact anatomical tip or joint.

If a statistic flags visually coherent movement, inspect its extraction and
sampling before changing anatomy. A reviewed statistical artifact may remain a
visible diagnostic only with an explicit reason and a tightly bounded case tied
to the source hashes, rendered RGBA view, export geometry, registration, metric
configuration and observed-value band. Changed inputs invalidate that case.
Retain the default bounds and real rejected-art controls; a blanket exemption
is not evidence that the movement was repaired.

For a regression check intended to catch a visible defect, retain a small,
hash-bound rejected-art fixture and demonstrate that the check rejects that
specific defect before applying it to the corrected drawings. An invented
coordinate jump alone does not prove that extraction detects the original art
failure. Completion, frame-count and export checks remain separate evidence.

If a regional statistic flags a visually continuous bend or a change in which
pixels contribute, retain the measured excess and the review explanation.
Use a diagnostic or an explicitly reviewed, image-bound case rather than
distorting coherent anatomy, moving the measurement window to hide the result,
or silently relaxing a general threshold. Changed artwork needs fresh review.

Inspect a loop as a periodic motion path: compare position **and velocity**
through the final two and first two poses, allowing authored acceleration and
projection. Similar endpoints can still hide an abrupt reversal or a held pose
followed by a reset. A passing metric supports review; it cannot certify anatomy,
weight, cloth continuity or the complete performance by itself.

When a viewing tool supports it, inspect actual normal-speed playback as well
as consecutive frames. If that capability is unavailable, state that limitation
and identify the frame sequences, stills and measurements actually inspected.
Generating a movie or running a paced capture is not evidence that it was watched.

### Completion checklist

- [ ] Approved design and direction references; explicit anatomical sides.
- [ ] Coherent full-body drawings; all four limb paths account for occlusion.
- [ ] Continuous support, passing and contact; no parked-foot snap or extra limbs.
- [ ] Stable head/torso proportions and landmark registration; deliberate modest bob.
- [ ] Correct directional costume/hair, material-appropriate secondary motion, readable outlines.
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
| Legs race below an almost fixed weapon carry | Gait too fast and upper-body action under-authored | Review cadence separately from FPS; redraw bent-arm pumps, shoulder/pelvis counterrotation and equipment response. |
| Hair or cloth pops between held silhouettes | Secondary motion lacks a continuous path across source batches | Draw material-specific lag and traveling bends; preserve attachment/volume and inspect each batch join. |
| First frame pops after the last | Endpoints and secondary motion were reviewed separately | Inspect the loop seam as an ordinary adjacent pair and draw its missing transition. |

## 10. Cinematic performances and finite actions

Build each performance around the character's approved directional references.
For current Iselin, retain white hair, blue eyes, blue/silver royal clothing,
the mantle on anatomical right, the forward braid on anatomical left and a
readable black exterior outline. Use the approved pixels as palette references.
Keep crown, head width, neck, shoulders and pelvis coherent across poses; inspect
the whole figure rather than stretching a body to match a hand or foot target.
Her arrival acting should convey composure, warmth and fatigue through restrained
head, shoulder and hand movement. Establish key poses before intermediate frames.

The old arrival playback is removed; its approved drawings remain reusable
character libraries, not live quest bindings. Camera presentation and source
density stay separate. The retained Iselin libraries use:

| View | Source canvas and registration | Presentation |
| --- | --- | --- |
| Ordinary world and seated meal | 24×36, draw anchor `[12,30]`, ordinary foot reference `[12,34]` | One artwork pixel per world pixel; 8×4 ordinary collision probe. |
| Arrival gate approach, stop and greeting | Complete detailed drawings sampled directly onto 80×96, anchor `[40,92]` | Approved cinematic detail matching the page and Lucan; no 24×36 intermediate. |
| Other arrival ground performances | 24×36, ground reference `[12,34]` | Uniform nearest-neighbor enlargement by `80/34` into 80×96, anchor `[40,92]`. |
| Arrival aerial shots | 16×24, ground reference `[8,22]` | Uniform nearest-neighbor enlargement by `1.5` into 48×64, anchor `[24,56]`. |

These are existing camera contracts, not permission to scale each drawing by its
occupied bounds. A larger action canvas requires an explicitly registered anchor
and visual review. Preserve ordinary collision, authored travel positions and
scene perspective when changing artwork.

The detailed gate bank is a scoped cinematic exception approved separately from
the ordinary native actor. Its final walking poses anticipate this particular
stop; select `gate_walk_left` and `gate_stand_left` for that performance rather
than replacing the generic looping `walk_left` used by longer travel shots.
The aerial descent uses `gate_incoming_left`, a separately reviewed cycle of
the first eight approved poses, so it joins the detailed ground shot without
repeating the later stop anticipation. Its 16-pixel stride keeps the same
two-pixel spacing per pose as the sixteen-pose ground approach.
The [live gate integration review](reviews/iselin_detailed_gate_live/README.md)
records the approved pixels and production selection.

### Entry, hold, recovery and rest

A one-time action has an authored entry, a stable hold, a recovery and a settled
rest pose. Frame counts and individual exposures follow the action; a greeting
does not inherit a walk's sixteen-frame budget. Draw complete, coherent frames
for head turns, gestures, stops and sit/stand transitions. Review near/far limbs,
costume overlap, support contacts and modest cloth/hair follow-through.

Choose either a finite hold or a player-paced hold released by the scene. A long
reading pause should leave the character in a comfortable resting pose. Trigger
each performance with a stable cue identity so pagination or repeated input
cannot restart it. Early release should finish the entry and recover coherently;
scene exit or Skip releases presentation ownership immediately. An action's
visual completion alone must not award inventory, quest facts or object transfers.
Actions that manipulate props additionally follow the interaction standard's
approach, facing, transfer cue and ownership rules.

Advance action clocks through scene updates. Rendering samples the current pose
without advancing time. Pause and focus loss freeze entry, hold and recovery.
Phase changes, restart, restore, Skip and closing a Gallery session discard
temporary action state. It is not part of the journey save schema.

### Focused review

Give each new performance its own key-pose and motion review. Compare the entry
and recovery against the actual preceding and following poses. Present numbered
frames, normal/slow playback and the performance in its production shot with the
other cast, camera scale, furniture and foreground occlusion intact. Review a
long hold, early release, repeated cue, pause/resume and scene exit alongside the
normal action. Keep unrelated approved animations unchanged.

A playback probe assembled from existing stills demonstrates clock and lifecycle
behavior. Label it as a synthetic probe; it is not a newly authored performance
or evidence that intermediate motion is finished. Keep review commands and
scene-specific clip schemas in the relevant scene guide and tool catalogue.

## Implementation references (examples, not competing standards)

- [Native idles](reviews/iselin_native_idles/README.md): approved directional
  appearance, consistent body scale and ordinary pixel density.
- [Native front walk](reviews/iselin_native_front_walk/README.md): complete-frame
  sources, 16-frame cadence and protected approved head pixels.
- [Native left walk](reviews/iselin_native_left_walk/README.md) and
  [native right walk](reviews/iselin_native_right_walk/README.md): complete
  directional drawings, near/far limb exchange and asymmetric costume sides.
- [Native rear walk](reviews/iselin_native_back_walk/README.md): restrained rear
  reach, crown/waist registration and foot-contact inspection.
- [Native gameplay integration](reviews/iselin_native_integration/README.md):
  current actor, scene and lifecycle verification. Individual approval captures
  remain historical snapshots at their recorded commits.
- [Cinematic walk stop](reviews/iselin_walk_stop/README.md): complete stopping
  drawings, exact walk/idle handoffs, decelerating root travel, a stable settle
  and continuous production-shot review.
- [Asset tool catalogue](../tools/README.md): current reproduction commands and
  local implementation facts.
