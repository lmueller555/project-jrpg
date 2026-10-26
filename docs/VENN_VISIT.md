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

- **Use borrowed tools:** Caelan kneels, reseats the pin with the mallet, walks
  south along the dry bank, pulls the debris out, returns and raises the board.
- **Use modest magicks:** Caelan raises an open casting hand, draws the existing
  water upstream into a visibly held crescent, and keeps that hand steady while
  crouching to straighten the pin with his other hand. He holds the water aside
  while lifting the gate, then lowers the casting hand. Released flow visibly
  carries the twigs south before normal control returns.

Both succeed without combat, a timer, a failure roll, resource costs or a major
branching consequence. Full flow propagates down the existing irrigation route
and over its south-facing spillway. No water moves uphill across a terrace.
Return through the cottage door and approach either parent for the approved
conversation about pumps, payments and the restored channel. Only finishing that
conversation completes the Venn objective.

The last of the two order-flexible households makes MQ01 ready for Serene's
existing report/turn-in dialogue. This feature does not add the staged mill
failure or MQ02 handoff.

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
board/pin before the quest gate is drawn. Repair poses keep logical feet on valid dry ground. The magick branch has
independent casting and working arms, with hand contact registered to the pin
through repair and opening. Its held-water overlay replaces only water-colored
gate pixels, so the opaque gate patch no longer hides the effect and wood, iron
and stone still occlude it correctly. Water remains in the existing eight-pixel
channel. Downstream flow and debris movement begin on release, not while casting.
The tools branch retains its original work poses and timings.

Water overlays reuse the approved channel and spillway frames, beneath actors.
They never mutate cached town ground, the collision mask, elevations, buildings
or the mill race. Elira's lantern remains in her saved ownership model: if still
carried, Caelan asks to set it down safely before taking supplies or tools in hand.

Only short physical actions control Caelan's body. Dialogue/choices stay live,
with the existing portrait bubbles and fonts. Click a response to select a method;
Space/E and clicks outside its buttons cannot choose. Walking away discards an
unfinished inspection, conversation or choice callback. Pause and inventory
freeze actions, and resize/text-size changes keep response hitboxes aligned.

## Durable progress

The optional version-one `venn_visit` journey record stores the completed
inspection IDs, `tools`/`magicks` method and repaired flag. Inventory separately
stores the recovery-supply receipt. Impossible progress before unlocking or
without the receipt is rejected before loading. A finished repair and unread
closing conversation survive room changes and reloads. Repeated visits never
consume a second bundle or repeat completion.

An interrupted gesture resumes on dry ground with the inspections/method retained
and the gate jammed; the player can choose again. No borrowed tool is lost or
consumable spent. Restoring a completed older objective opens the gate without
inventing which method was chosen. New Game resets the gate, supplies, inspection
facts, method and actor pose.

`tools/build_venn_visit.py` rebuilds the family, poses and gate overlays.
`tools/export_dialogue_portraits.py` exports all three portraits. Integration
tests in `tests/test_venn_visit.py` exercise real doors, proximity dialogue,
inventory contact, two inspections, both clicked methods, both household orders,
water/collision preservation, interruption/reload, old saves, large text and
letterboxing, pause and unfinished closing prose.


## Magick repair animation

`venn_magicks.py` loads the explicit pose sequence, source-layer atlas and water
levels from `assets/story/venn/magicks/`. Rebuild them with
`python tools/build_venn_magicks.py` (Pillow). The old four generic
`caelan/magicks_N.png` frames and ripple renderer are removed. The general Venn
builder no longer regenerates them and invokes the new builder instead.

The stages are raise hand, ease water, hold water, work pin, open, release water
and finish. Interrupted casts retain the chosen method and inspection facts but
restart safely with the gate jammed; completed older magick repairs stay repaired
without replaying the new animation. Pause and inventory freeze all pose/water
clocks. The family's closing conversation still completes the objective.

See the [in-game close-up](reviews/venn_magicks/README.md).
