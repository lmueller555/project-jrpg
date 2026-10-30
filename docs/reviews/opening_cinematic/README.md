# Opening cinematic review

[Watch the full cinematic with music](opening_cinematic.mp4).

This capture follows the production title's **New Game** path through the
complete opening, an Esc pause/resume demonstration and the ordinary bedroom
handoff. All images are rendered by the game with the runtime assets. Temporary
journey and settings files leave ordinary saves untouched. Effects are muted.

The expanded scene lasts 252.6 seconds and presents all
30 user-authored dialogue lines. The choreography includes
putting the cup down, holding hands, walking to and repairing the lamp, the
blue flare/firework and persistent sky light, the return shot, and the departure
past an anonymous bloodstained helmet. Actor and camera actions receive their
own authored time; ordinary dialogue gaps remain short.

Dialogue uses the same bordered panel, left speaker portraits, gold names,
typography and text spacing as normal gameplay. Longer lines turn through
timed pages inside their existing dialogue holds, with no click-to-continue
prompt. Every page is observed in the full capture. Departure movement is 20%
faster (48 pixels/second); the walking animation keeps its 180 ms frame cadence.
The camera follow is retimed to keep the helmet centered, followed by the
existing slow zoom and fade after both characters leave.

The soundtrack is reconstructed from the exact shipped OGGs and observed
production mixer commands because the headless SDL driver has no audio loopback.
It includes the actual fades and the preserved music position across the pause.
It is not a separate musical arrangement. `verification.json` records the
observed route, all dialogue lines and gaps, single repeating leitmotif request,
frozen-world checks, longest-caption layout and the new sequence barriers. The
two-second Esc demonstration occurs during the flare flight, freezing its
motion, the camera and the same music playback position.

- [Handholding close-up](handholding_closeup.mp4)
- [Flare flight, firework, sky light and completed repair](beacon_sequence.mp4)
- [Departure and helmet ending](helmet_ending.mp4)
- [Four visible lamp repair stages](lamp_stages.png)
- [Automatic paging at 480×320 with 150% text](large_text_paging.mp4)
- [Both large-text pages and their display times](large_text_pages.png)

These short clips are consecutive production-rendered frames with no audio;
the full preview above includes the complete soundtrack.

The accessibility paging clip separately renders the original eight-second
lamp request through production `Game.draw` at 480×320 with 150% text. It shows
both balanced pages using the original timed hold, with no soundtrack or input
required. It does not change the default-size full playthrough above.

[Watch the corrected drinking motion close-up](drinking_closeup.mp4) or inspect its
[rest → lift → sip → lower → rest frames](drinking_keyframes.png). These are
consecutive production world frames, cropped and enlarged at an integer scale;
the short close-up has no audio.

- [Valley establishing shot](valley.png)
- [Lantern-lit sanctuary](lantern_reveal.png)
- [Conversation](conversation.png)
- [Quiet exchange](quiet_exchange.png)
- [Cup placed on the bench](cup_on_bench.png)
- [Mira holding both hands](handholding.png)
- [Mira working on the lamp](lamp_work.png)
- [Flare ascent](flare_ascent.png)
- [Firework burst](flare_burst.png)
- [Persistent sky light](sky_glimmer.png)
- [Camera returning to the pair](camera_return.png)
- [Restored lamp](lamp_stage_3.png)
- [Walking departure](departure.png)
- [Passing behind the foreground sword](foreground_pass.png)
- [Helmet centered; camera held](helmet_centered.png)
- [Both actors offscreen](actors_offscreen.png)
- [Helmet before the fade](helmet_before_fade.png)
- [Helmet close-up](last_look.png)
- [Final helmet fade](helmet_fade.png)
- [Esc pause](paused.png)
- [480×320 with 150% text](minimum_large_text.png)
- [Bedroom handoff](bedroom.png)

Rebuild from the repository root with:

```sh
python tools/capture_opening_cinematic.py
```
