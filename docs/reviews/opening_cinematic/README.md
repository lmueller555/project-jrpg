# Opening cinematic review

[Watch the full cinematic with music](opening_cinematic.mp4).

This capture follows the production title's **New Game** path through the
complete opening, an Esc pause/resume demonstration and the ordinary bedroom
handoff. All images are rendered by the game with the runtime assets. Temporary
journey and settings files leave ordinary saves untouched. Effects are muted.

The expanded scene lasts 198.7 seconds and presents all
30 dialogue lines. Its ordinary gaps are one second;
two four-second acting pauses retain room for the drink and final preparation.

The soundtrack is reconstructed from the exact shipped OGGs and observed
production mixer commands because the headless SDL driver has no audio loopback.
It includes the actual fades and the preserved music position across the pause.
It is not a separate musical arrangement. `verification.json` records the
observed route, all dialogue lines and gaps, single repeating leitmotif request,
frozen-world checks and longest-caption layout.

[Watch the corrected drinking motion close-up](drinking_closeup.mp4) or inspect its
[rest → lift → sip → lower → rest frames](drinking_keyframes.png). These are
consecutive production world frames, cropped and enlarged at an integer scale;
the short close-up has no audio.

- [Valley establishing shot](valley.png)
- [Lantern-lit sanctuary](lantern_reveal.png)
- [Conversation](conversation.png)
- [Quiet exchange](quiet_exchange.png)
- [Final look](last_look.png)
- [Esc pause](paused.png)
- [480×320 with 150% text](minimum_large_text.png)
- [Bedroom handoff](bedroom.png)

Rebuild from the repository root with:

```sh
python tools/capture_opening_cinematic.py
```
