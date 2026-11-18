# Tomas native activation review

## Scope

Explicit persistent ID `tomas` selects the canonical named base and dormant
native action bank. Original generated map records, schedules, collision,
positions, dialogue/quest flags, cues, logical anchors and prop ownership remain
unchanged. No Sanctuary gardener, Serene, other character or cinematic bank is
rebound. Original Tomas portrait remains byte-identical to the canonical one.

## Native routing

- RoutineNPC: named four-direction idle/walk plus64x48 logical padded action
  canvas. Canonical base design metadata is separate from action canvas metadata.
  Only Tomas's bundle/stack/model room props select matching native versions.
- Opening: Tomas breakfast bodies and explicit walk loader select native art;
  existing plate, fork, cup, table/chair positioning and timings remain owned by
  the original controller.
- Halden visit: Tomas's36 sack poses and the three copies of the same shared sack
  use native art; Caelan's poses, pallet, medicine, custody and contact state do
  not change.
- Regent meal: own right-facing seated/eat keys replace Tomas's old runtime flip
  so his anatomical left-knee patch is not mirrored onto the near right leg.
  Other actors retain their own existing transforms and adapters.
- Four RegentArrival cinematic poses retain original pixels and projection.

## Evidence

`tools/capture_tomas_hd_integration.py` renders native960x640 frames through
`Game.draw`. Routine work, Opening eating and Regent seating are explicitly
staged pose reviews, not claimed full-playback recordings. The Halden lift is
captured after actual quest acceptance, conversation, interaction and updates.
All six PNGs were visually inspected, including a magnified native crank/contact
crop. Native source contact boards inspect every action key separately.

Validated in isolated sparse workspace with read-only links to unchanged assets:

-6 focused production-Game native integration tests
-10 existing Tomas routine tests (full route, prop custody, conversation/door wait)
-11 existing Halden gameplay tests (lift/store contact, persistence, follow/return)
-15 Opening sequence tests (legacy fixture compatibility and choreography)
-14 Regent action tests (scene ownership, timing, seating and interruption)
-6 dormant native art/provenance/timing tests
-Exporter `--check`: byte-exact

The Opening unit fixture intentionally remains legacy to confirm fallback;
production-Game native integration covers the new binding separately.

## Dependencies and shared merge boundary

Requires the canonical `assets/characters/named_hd/tomas` bank and dormant
`assets/characters/tomas/activity_hd` package, including right-facing meal keys.
For Serene's sibling activation, combine the independent actor-ID branches in
RoutineNPC; preserve both native scene adapters in RegentActions by nesting
Serene's image adapter as Tomas's legacy fallback. Neither should replace the
other actor's binding. No source map regeneration is required.
