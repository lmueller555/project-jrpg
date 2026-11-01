# Checkpoint familiarity and optional participation capture

`checkpoint_charm_preview.mp4` concatenates the **complete** normal-speed guard,
overlook bench, farm cat and unfinished masonry clips. Individual MP4 files
contain the same footage and accepted regional effects. Acknowledged dialogue
pages remain visible for at least 2.2 seconds; cancelled lines are labelled.
Site cuts are identified in report markers.

Reproduce from the repository root with `python tools/capture_checkpoint_charm.py`
in the project environment (pygame, NumPy and ffmpeg required). Use `--clips
guard`, `bench`, `cat` or `masonry` to record a subset. Simulation runs at 30 Hz,
the actual gameplay canvas remains 480×320, and the window/video is 960×640 at
15 fps. No playback acceleration or camera zoom is applied.

Only the shipped MQ01–MQ03 predecessor quests and initial player positions are
fixtures. New scene clocks, routes, seats, cat modes and worker progress are
never seeded. Inputs use production `handle_events`, movement through
`Game.update`, and the normal `overworld_travel.interact` path.

The guard clip includes the full approach, seat exchange, seven acknowledged
lines, five physical contacts, both guards' complete return to duty and the
quieter repeat. It also includes an exact mid-seat-action Save/Continue,
walking out of dialogue to cancel an unread line, walking back and pressing E
to resume it, and repeated E beside the moving guard without a generic guard
conversation taking ownership. Story flags remain unchanged.

The bench clip shows E sitting, repeated keys, a paused seated state, exact
seated Save/Continue, standing through E, Escape and directional movement, and
explicit cancellation. Physical feet remain on the clear canonical standing
point; the authored sitting sprite uses the existing bench. The cat clip
cancels an unfinished greeting by walking away, then acknowledges a later E
greeting through the existing wildlife owner's silent stretch. The masonry
clip uses real worker sorting, reads the unfinished-project text, and waits
for actual tool contact. Tea is never started and the crossing stays unfinished.

Pause is opened through the production `pause.open()` API because Escape while
seated is the stand/cancel action. Save/title/Continue uses `save_progress()`,
the title state and production `begin_journey(True)`. These boundaries are
explicitly labelled in input traces. Immediate post-Continue display stills can
be black during the normal opening fade; `*_after_continue_visible.png` shows
the subsequent visible scene. Exact state comparisons occur before that fade
advances.

Audio follows `tools.capture_regional_audio.Recorder`: SDL's dummy device is
not recordable, so accepted production PCM, source gains and stop events are
rendered offline at 48 kHz without normalization. Music is muted. Reports retain
the actual source position, listener, distance, gain, family, priority and
hearing boundaries for every accepted start. MP4 audio is AAC. Source WAV files
and lossless native world-frame archives remain outside the repository under
`/tmp/checkpoint-evidence` (override with `CHECKPOINT_FRAME_ARCHIVE`). Every frame
in each new lossless archive is decoded and checked against its recorded RGB
SHA-256. Native world frames exclude the separate HUD/dialogue overlay; the
display MP4 and display stills include it. This evidence does not claim a live
device recording or subjective listening assessment. The cat response is
intentionally silent; any nearby water/foliage sound retains its real owner.

Representative frames were inspected with `view_image`: the guard banter and
return, cancellation, overlook sitting and standing, cat stretch, and masonry
inspection. They show one original pair of guards, one original seat at each
site, clear Caelan feet, the cat beside Caelan, readable dialogue and the
unfinished crossing. No duplicated actor/prop or obvious clipping was observed.
The guard dialogue bubble overlaps part of the bench/borrower; the supplied
native world still shows the complete placement. The predecessor-fixture quest
tracker is the normal game HUD and is unrelated to these optional actions.

`capture_summary.json` indexes durations and checks. Each `*_report.json`
contains markers, exact Continue snapshots, input/state traces, source-file
hashes and audio events. `*_frames.json` records native/display RGB frame hashes.
`media_probe.json` verifies the delivered video/audio stream formats.
`SHA256SUMS` covers the review deliverables.
