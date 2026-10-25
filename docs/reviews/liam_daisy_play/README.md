# Liam and Daisy's shared play routine — awaiting review

- [Full cycle, including the drinking outcome](full_cycle.gif)
- [Invitation, two hops and excited wag](invitation.gif)
- [Three-lap chase with the approved running sprites](chase.gif)
- [Return home: drink, then rug](drink_first.gif)
- [Return home: straight to the rug](skip_drink.gif)

These are captures of the production `main.py` simulation and renderer at actual
speed. Only the initial randomized wait is skipped. The camera switches between
the actual home and town scenes; no actors are cloned for the preview. A short
resting hold ends each loop, rather than showing the entire nap or cooldown.
GIF replay resets the preview, not the in-game water bowl.

The first invitation becomes due after 20–40 seconds. Liam waits until Daisy is
resting or pausing with no active bowl reservation, finds a nearby clear spot,
and asks “Want to play, Daisy?” in an overhead bubble. It does not open modal
dialogue or lock player controls. Daisy stands, hops twice, and wags. They queue
through their door individually, line up in the lower-ground front yard, then
follow a rounded oval for three laps. Tight turns are slower; Liam waits if
Daisy is delayed. Both use their approved four-frame runs and walk indoors.

Liam settles with his head on the pillow and the quilt covering his body. A
single random roll on Daisy's return gives a 50% chance of drinking first,
otherwise she goes directly to her rug. Drinking consumes one existing fill
level and resets her normal water cooldown. Empty water gets inspection only;
there is no automatic refill. She stays on her rug if Liam is delayed at his
bedside. Their joint nap lasts 45–90 seconds, then Liam gets up beside his bed
and Daisy resumes her approved normal routine. Repeat cooldown is 8–12 minutes.

The same actor instances move between cached scenes and continue offscreen.
Player-blocked routes wait or detour, including transfer landing points. Liam's
parents remain stationary and silent. No quests, new portraits or family refill
routines are introduced.

Reproduce with `python tools/build_liam_family_home.py`, then
`python tools/capture_liam_daisy_play.py`. `captures.json` records both outcomes,
scene transfers and final positions; `validation.json` records checks.
This work is published for review and has not been merged into main.
