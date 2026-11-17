# Liam’s house animation audit

[Liam’s house in the combined build, at native game resolution](liam_house_native.png)

| What changed | Production-game evidence |
| --- | --- |
| **Daisy’s bowls.** Food and water now show full, half-full and empty without changing the ceramic bodies. Daisy uses each bowl’s exact rim at mouth contact, and water ripples stay on the remaining water surface. | [Bowls before/after and two depletion clips](../liam_interior_audit/README.md) |
| **Fireplaces.** The flames flicker from a fixed fire bed inside the opening. Logs, brickwork and the hearth edge stay fixed. All 11 rooms using the shared animated hearth receive the correction. | [Four phases, repeated loops, and shared fireplace views](../liam_hearth_animation/README.md) |
| **Liam’s blocks.** A single box follows the room’s top-down perspective. Its front is the same piece of art through every grab and return. Each block stays accounted for as it moves between the box, Liam’s hand and the floor. | [Pickup, put-back, fill states and four carry directions](../liam_block_box_audit/README.md) |

## Integrated validation

Reproduced on the combined production revision `6c53da585c2fa68700e20ce0292afcb13164ad18`
over `5630648b4fe9cb79ae7b1ad867b4aa5b6e0cc836`. The tester uses the production
Game/World and shortens only the initial waits in the visual fixtures.

- Two completed visits each to food and water depleted full to half-full to empty.
  Same-session room re-entry and the existing fresh-session defaults are retained.
- Captured 11 shared fireplaces at all four phases, three consecutive Liam-room
  loops, actor depth overlap and six widely separated Reduced Motion samples.
- Ran a complete Liam build and cleanup cycle and captured all four carry
  directions. The front layer is an exact subset of all 32 box states.
  Focus/pause, interrupted pickup, quest handoff, and return/re-entry checks are
  covered in the focused regression run.
- Positions, supports, sort anchors, doors, collision, room layout, quests and
  save format are unchanged. Only the two bowls and block-box visual records
  changed in the Liam room map. The town and all other live interior maps are unchanged.
- The registered bowl, hearth-only, settlement and town rebuilds are
  deterministic; the town composer verified all 997 outputs.

The [validation record](validation.json) summarizes the focused tests. The one
unrelated Liam exterior/door assertion already failed identically on the
unmodified baseline. The full repository suite was not run.
