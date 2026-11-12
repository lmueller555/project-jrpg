# Character–object interaction standard

This is the mandatory global standard for player characters and NPCs manipulating
objects in cutscenes, scripted scenes, routine work, and gameplay interactions.
It governs new work and corrections to existing interactions. Read it alongside
[personal-prop visibility](PERSONAL_PROPS.md), which covers when personal tools
and equipment appear or disappear.

This standard supersedes conflicting guidance in older scene documents, asset
recipes, tests, and historical reviews. Existing captures and exact-contact
coordinates describe implementations; they do not impose a global requirement
for pixel-perfect hand contact or certify every current NPC as compliant.

## Governing principle

Convey the intended action with believable staging, recognizable animation,
natural body proportions, and correct visual depth. Exact hand-to-object
contact is optional. A small, deliberate object snap is acceptable when an
appropriately positioned character's natural reach gets reasonably close.
Never stretch limbs, enlarge hands, warp a body, or slide planted feet to force
contact. If the gap is too large to read convincingly, change the approach,
work station, facing, animation, or prop placement.

## Required sequence

**Approach → face → animate → snap/transfer → finish.**

1. Approach a reachable work station near the actual object. Check collision,
   other actors, furniture, and foreground occlusion. Interaction-trigger range
   alone does not establish a convincing animation position.
2. Face the object before manipulating it. Select artwork appropriate to the
   action, actual facing, and camera view. Preserve physical handedness and
   asymmetric clothing or worn equipment.
3. Perform a recognizable reach, grasp, lift, lower, place, push, or other
   relevant action. Bending and crouching use natural joints and retain the
   character's approved proportions and ground registration.
4. Resolve the transfer at a deliberate cue, normally when the grab or placement
   animation completes. Until then, retain the object's previous owner/location.
   At the cue, snap to the authored grip, attachment, support, or destination.
   A modest reach gap may close at this snap; it must not disguise a remote grab.
5. Finish the action and recover to an appropriate pose. Deposited objects stay
   at their destination. Personal tools and weapons disappear when their use
   ends, before ordinary travel resumes.

The visible action must precede its result. Playback must not complete a
pickup, placement, or other required action merely because dialogue advances.

## Object ownership and transfer examples

An object has one authoritative owner and one visible location at a time.
Ownership can be a world station, a character's grip, or another attachment.
Remove the old representation at the same cue that publishes the new one.

| Action | Before the cue | At the cue and afterward |
| --- | --- | --- |
| Pick up a sack | Sack remains on the pile while the worker reaches/lifts. | Snap to the directional holding position; remove it from the pile. |
| Place a toolkit | Kit remains held during the lowering action. | Snap to the work surface; it stays fixed when the character moves away. |
| Hand over a cup | The giver owns the cup while the recipient reaches. | Transfer once to the recipient's grip, with no duplicate cup. |
| Attach a pail to a hook | Character supports the pail during the attachment action. | Snap to the hook's attachment; subsequent motion follows that mechanism. |
| Move a crate | Character approaches, faces it, and performs the moving action. | Resolve at the authored destination, or follow a deliberately animated supported movement. |
| Finish using a personal weapon | Weapon appears during its authored presentation/use. | Hide it when use ends; ownership and equipped state remain unchanged. |

Anchors describe intended grip, support, destination, and ground positions.
They do not require every intermediate hand pixel to touch the object. Preserve
stable character scale and feet across pose changes and larger action canvases.

Continuous actions such as pouring, turning a crank, pushing, or lowering a load
may animate the manipulated object throughout the action. Keep their attachment
and support believable. Do not interpolate a loose prop across the gap between
source and grip merely to manufacture contact. Fixed supports, posts, and
unmanipulated scenery remain stationary.

## Camera, facing, and occlusion

Evaluate depth in the actual camera view. A world object's apparent screen
position alone does not decide whether it is in front of a character.

| View or arrangement | Required treatment |
| --- | --- |
| Character faces the camera with an object held in front | Render the held object in front of the appropriate torso area, with hands layered as the grip requires. |
| Character turns their back to the camera | Render the held object behind the body. Opaque body pixels obscure overlapping portions; exposed edges may remain visible. |
| Character is viewed from the side or obliquely | Use the appropriate grip and layers for the near/far arms and object. Do not reuse a front overlay indiscriminately. |
| Object is being deposited behind an actor or piece of furniture | Keep the correct occlusion through the placement and snap. The object must not flash through the occluder at transfer. |
| Object has been placed | Use its destination's world depth, surface support, and foreground occlusion independently of the former holder. |

Apply these rules during approach, turning, use, transfer, and recovery—not only
at the first or last frame. A completely hidden held object is valid when the
body is between it and the camera. Do not draw through the character to keep a
prop visible. Transparent canvas padding must not act as an opaque rectangle.

## Personal props and ongoing carrying

Equipment ownership does not automatically create a separate visible prop.
Hide personal weapons, kits, and tools after their authored use, as specified in
[PERSONAL_PROPS.md](PERSONAL_PROPS.md). Clothing and worn rigs remain part of the
character design. An explicit carrying or delivery action can retain a held
object until that task ends; it still requires directional grip and occlusion.

Deposited items remain fixed in the world when the character departs. Decorative
prop transfers do not grant inventory, healing, rewards, or quest progress
unless those effects are independently part of the authorized gameplay design.

## Timing, interruption, and restoration

- Trigger each transfer and associated sound once at the defined action cue.
- Keep required actions intact for both slow reading and rapid confirmations;
  a held dialogue page must not restart a completed pickup or delivery.
- Pause and focus loss freeze the action, object state, and its sound together.
- Cancellation, scene exit, and Gallery restart clean up temporary ownership,
  overlays, and audio without creating a second object or leaving a floating one.
- Save/Continue reconstructs a coherent owner, location, facing, and action state
  using the scene's existing checkpoint model. A committed transfer must not be
  rewarded or duplicated again. Replaying an unacknowledged beat must rebuild
  that beat's consistent starting arrangement.

## Required review and acceptance

For new or corrected interactions, verify the following in the actual scene:

- The character reaches a sensible nearby station and faces the object.
- The intended action is readable at native gameplay scale; limbs, hands, body
  scale, and foot placement remain natural throughout.
- The snap is small, deliberate, and synchronized with the action's cue.
- There is one object representation before, during, and after the transfer.
- Front, rear, side, and any used oblique views have correct body/prop layering;
  placement and movement respect furniture and foreground scenery.
- The deposited object's destination and support are convincing, and personal
  props disappear after use rather than floating alongside ordinary travel.
- Blocked approaches, slow/rapid input, pause/focus changes, cancellation, scene
  transfer, Gallery restart, and applicable save/Continue boundaries remain sane.

Use focused automated checks for ownership, cue boundaries, cleanup, depth, and
restoration, plus visual inspection for anatomy and readable intent. A missed
pixel-perfect contact is not a failure by itself. An exact-contact test may
protect an intentionally registered scene, but must not force unnatural anatomy
or override this standard. Record which interaction, views, and lifecycle states
were checked; completion-only tests do not establish visual quality.

## Related implementation guides

- [Regional NPC work and transfers](REGION_NPCS.md)
- [Garden and orchard interactions](GARDEN_ORCHARD.md)
- [Mill quest work stations](MILL_QUEST.md)
- [Sanctuary arrival performance](SANCTUARY_ARRIVAL.md)

These guides retain local implementation details. Historical review material is
preserved as evidence of earlier work; conflicting prescriptions defer to this
standard. Documentation adoption alone does not repair existing runtime behavior.
