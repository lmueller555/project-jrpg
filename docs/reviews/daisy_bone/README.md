# Daisy's play bone — awaiting review

- [Bring the bone to the rug, bow, shake and chew](rug_play.gif)
- [Drop it elsewhere, then find and retrieve the same bone](drop_and_retrieve.gif)
- [Carrying views in all four directions](carrying_directions.png)
- [Initial bone placement beside the rug](room_overview.png)

These are actual `main.py` room renders and production routine updates at normal
speed. The review starts each selected variation directly, skipping the initial
2–4-minute wait and the repeat cooldown between relocation and retrieval. Other
ambient work and feeding cooldowns are deferred during the capture so the bone
routine can be inspected clearly. A short hold shows each completed state.

There is one bone throughout. It transfers from the floor to Daisy's mouth at
the authored contact pose, follows the existing walking bob, then transfers to
her paws for chewing. The back-facing bone is hidden by her head while still
owned. On release the same bone returns to the floor; after relocation, it stays
at that new position and is retrieved from there in the next session. GIF replay
resets only the preview, rather than creating additional toys in the game.

The rug variation includes a small play bow, two head shakes, 15–25 seconds of chewing
and a two-pixel nose nudge. The bone uses a warm ivory palette and is nonblocking.
Pickup, drop, bow, shake, settle, chew, release, nudge and carrying loops all use
four poses. The standing walks preserve the approved dog artwork and timing.

`pickup_contact.png`, `drop_contact.png` and `rug_chewing.png` show enlarged
contact details. `bone_left_elsewhere.png` shows the persistent dropped location.
`captures.json` records actual states, transfers, positions, durations and the
verified single object identity across both sessions.

Reproduce with `python tools/build_liam_family_home.py`, then
`python tools/capture_daisy_bone.py`. This branch is published for review and has
not been merged into main.
