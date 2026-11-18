# Venn family: supplies and the irrigation gate

Finish Halden's visit and Tomas's departure first. The Venn family occupies the
wide eastern cottage, and their errand can be completed before or after Elira's.
The parents use the display names Mrs. Venn and Mr. Venn; their child is identified
by family role. Given names and exact ages remain open narrative details.

Approach either parent inside. Click through the approved exchange to hand over
the recovery supplies. Their child rests under the existing quilt; approaching
the bedside offers a brief optional conversation with no quest effect.

The existing gate is east of the cottage. **E** at its pin inspects the skewed
mechanism; **E** a little farther south inspects the blocked channel. Read both
observations, then return to the pin and press **E** to choose:

- **Use borrowed tools:** Caelan stands on the dry bank, reseats the pin with a
  mallet, walks south to clear the debris with a hook, then returns and raises
  the gate with the hook. The tool provides the reach while his body stays balanced.
- **Try magicks:** Caelan raises a bent arm and gathers a small blue-white spark.
  The energy wavers and fizzles. The three-second attempt does not push the water
  back or move the gate, pin or debris. He lowers his hand and says, "I can't move
  it. I'll need the tools." Acknowledging the line starts the practical repair.

The failed spell establishes Caelan's limited strength: he can produce a trace
of magical energy, but cannot yet exert enough force to move this water. The
outcome is fixed, with no retry roll, resource cost or penalty. After failure,
returning to the gate offers only the borrowed tools. Choosing tools directly
skips the spell attempt.

Only the tool repair restores the channel. Full flow propagates down the existing
irrigation route and over its south-facing spillway. No water moves uphill across
a terrace. Return through the cottage door and approach either parent for the
approved conversation about pumps, payments and the restored channel. Only
finishing that conversation completes the Venn objective.

The last of the two order-flexible households makes MQ01 ready for Serene's
report. The existing opening conclusion then stages Halden's arrival about the
stopped mill, completes MQ01 and unlocks the Mira/MQ02 handoff.

## Visual and interaction ownership

`venn_visit.py` registers one family in the existing room. Directional sprites
reuse the approved adult and child silhouettes: a teal dress/flax apron, rust
work vest/oatmeal sleeves, and a small blue nightshirt. Three independent 72×72
portraits retain their generated masters. The resting head sits on the pillow
above the quilt, with an occasional blink; the original bed owns collision.
An empty bedside foot rectangle still permits normal proximity conversation.

The working pin is on the west, accessible bank. The quest gate frames use the
approved mechanism with that pin relocated; the shared gate generator keeps
its original right-pin default. A small opaque background removes the old baked
board/pin before the quest gate is drawn.

The failed cast uses the approved standing pose study. Its head, hips, legs and
boots keep their normal idle positions and proportions; only the near forearm
rotates, with a small spark beyond the palm. The last frame returns to the exact
idle sprite. There is no forward torso translation, patched trouser shape,
crouch, gate contact or held-water overlay. The practical repair also uses
grounded standing poses, with a mallet and hook making the physical work readable.

Water overlays reuse the approved channel and spillway frames, beneath actors.
They never mutate cached town ground, the collision mask, elevations, buildings
or the mill race. Casting leaves the existing water and debris state unchanged.
Elira's lantern remains in her saved ownership model: if still carried, Caelan
asks to set it down safely before taking supplies or tools in hand.

Only short physical actions control Caelan's body. Dialogue/choices stay live,
with the existing portrait bubbles and fonts. Click a response to select a method;
Space/E and clicks outside its buttons cannot choose. Walking away discards an
unfinished inspection, conversation or choice callback. If Caelan leaves before
acknowledging the failure line, the tools-needed checkpoint remains available at
the gate. Pause and inventory freeze actions, and resize/text-size changes keep
response hitboxes aligned.

## Durable progress

The optional version-two `venn_visit` journey record stores the completed
inspection IDs, original `tools`/`magicks` choice, repaired flag and
`magicks_failed` milestone. Inventory separately stores the recovery-supply
receipt. The original choice remains `magicks` when the failed spell is followed
by a successful tool repair; it does not imply a magical success. The failure is
also recorded as `CH01_MQ01_VENN_MAGICKS_FAILED`.

Impossible progress before unlocking or without the receipt is rejected before
loading. A finished repair and unread closing conversation survive room changes
and reloads. Repeated visits never consume a second bundle or repeat completion.

An interrupted cast before the failure checkpoint returns safely to idle with
the inspections and choice retained; the player can choose again. Once failure
has been recorded, walking away or reloading preserves the tools-needed state
and does not replay the cast. No borrowed tool is lost or consumable spent.
Version-one records remain accepted. Previously repaired saves, including older
successful magick repairs, stay repaired without inventing a failed attempt.
Restoring a completed older objective opens the gate without inventing which
method was chosen. New Game resets the gate, supplies, inspection facts, choice,
failure milestone and actor pose.

`tools/build_venn_visit.py` rebuilds the family, tools poses and gate overlays.
`tools/export_dialogue_portraits.py` exports all three portraits. Integration
tests in `tests/test_venn_visit.py` and `tests/test_venn_magicks.py` exercise
proximity dialogue, two inspections, both choices, unchanged water/gate/debris
during casting, tools fallback, failure/reload progress, source-pose preservation,
old saves, pause and the family's closing conversation.

## Failed magick animation

`venn_magicks.py` loads the explicit pose sequence from
`assets/story/venn/magicks/`. Rebuild it with
`python tools/build_venn_magicks.py` (Pillow). Its source layers are body,
casting arm and energy; `source_body.png` preserves the original idle reference.
The old generic casting frames, successful held-water effect and magick-specific
gate-opening atlas are removed. The general Venn builder invokes the new builder
and does not regenerate those superseded assets.

The stages are raise hand (650 ms), attempt (1100 ms), fizzle (600 ms) and recover
(650 ms). The first and last poses match idle on the existing town draw anchor.
The family's closing conversation still completes the objective after the tools
have restored the water.

See the [in-game scene preview](reviews/venn_magicks/README.md).
