# Daisy's house routines — approved

Captured from the actual `main.py` room renderer and state machine. Only the
initial long rug wait is skipped; approach/return travel and actions run at real
speed. GIF replay resets the preview scene; the game does not refill bowls.

- [Wander, pause and return to the rug](wandering.gif) — 2× whole-room view.
- [Complete eating visit](eating.gif) — 6× close-up; [four-pose slow detail](eating_slow.gif).
- [Complete drinking visit](drinking.gif) — 6× close-up; [four-pose slow detail](drinking_slow.gif).
- [Inspecting an empty bowl](empty_bowl.gif) — no chewing, lapping or consumption.

Daisy walks at 36 native px/s, rests 45–90 seconds, and wanders for roughly
20–40 seconds with 2–5 second pauses. Food cooldown is 2–4 minutes; water is
90–180 seconds. Eating lasts 7.2 seconds and drinking 4.8 seconds. Each completed
visit consumes one level: full → half-full → empty. Empty bowls get a 900 ms
inspection. Four-pose stand/settle and head-lowering/raising transitions connect
the approved lying and walking appearances to the new actions.

Food and water have separate approach points, keeping Daisy out of the other
bowl. Her muzzle meets the contents, the front wood occludes it, and water
ripples stay inside the fill mask. The bowls remain fixed. Daisy yields or
reroutes around the player and reserves a bowl until she steps clear.
Her routine and bowl states progress offscreen and persist on room re-entry
within the same game session. No family dialogue or refill routines are added.

Reproduce with `python tools/build_liam_family_home.py` and
`python tools/capture_daisy_routines.py`. See `captures.json` for visited states
and final positions, and `validation.json` for checks. The routines were approved by the user on 2026-10-25 for merging into main.
