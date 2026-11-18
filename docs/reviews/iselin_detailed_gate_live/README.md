# Iselin detailed gate performance — live integration

The user-approved detailed approach, eight stopping drawings and offset standing
pose now load through the arrival's production actor manifest. The performance
uses the same 80×96 canvas and `[40,92]` anchor as the page and Lucan. The ordinary
24×36 actor, four ordinary walks and portrait remain unchanged.

[Normal-speed live capture](normal.gif) · [Quarter-speed capture](slow.gif) ·
[Full arrival scene](greeting.png) · [Numbered production drawings](numbered_frames.png)

The detailed `gate_walk_left` bank belongs to the gate approach. `stop_left`
begins with its exact final drawing and recovers to `gate_stand_left`, which stays
selected during the greeting and initial admission wait. The visible aerial
lead-in uses `gate_incoming_left`, a dedicated cycle of the first eight approved
drawings with a 16-pixel stride; it reaches the identical first approach drawing
at the camera handoff. Later journeys retain the existing generic walks. The
sixteen-pose approach contains anticipation for this particular stop, and its
late tail is not repeated in the aerial lead-in or ordinary looping travel.
Turning, other directions, listening and gestures keep their current artwork.

## Production capture and approval evidence

The helper launches a real disposable arrival Gallery and stations only the
initial `gate_approach` shot at zero. All later poses, action cues, actor roots,
camera movement, occlusion and greeting transitions come from normal
`Game.update()` and `Game.draw()` calls. There is no injected candidate bank,
per-frame pose override or manufactured foot alignment. This is a continuously
updated selected shot, not a claim of a fully played arrival or quest walkthrough.

[Capture metadata](capture.json) verifies all 25 live PNG byte hashes and
production-loaded RGBA surfaces against the immutable
[approval snapshot](../../../assets/source/characters/iselin/cinematic_gate_left/approval.json).
The 101 selected image hashes, world roots and cameras match the previously
approved timed preview exactly. The report retains the approved capture's hash
and each expected image hash so this comparison remains inspectable without
relying on the temporary review checkout. All 69 approved ordinary idle, walk
and portrait PNGs also retain their recorded bytes.

Both GIFs contain the same 101 real rendered samples from approach time 0.8 to
2.8 seconds. Normal playback lasts 2,020 ms, and quarter-speed playback lasts
8,080 ms. Every decoded GIF frame and its exposure are verified. PNGs retain the
lossless rendered colors. The [world registration diagnostic](world_contact_board.png)
composes actual selected whole surfaces at their actual roots with one common
origin and anchor; it removes the camera pan for inspection, without aligning
individual feet.

The incoming 24-pixel/s movement, 1.25-second stop cue, six-pixel deceleration to
`[575,375]` at 1.75 seconds and 1.95-second greeting transition are unchanged.
The stop retains a 40 ms walk handoff, eight 60 ms drawings, a 60 ms hold and
120 ms recovery, totaling 700 ms. The final stop and standing image are exact
matches. Minor hand, hem and sole pixel variation remains in the approved art;
this is not a claim of mathematically perfect contact locking.

## Aerial lead-in and exact camera boundary

[Normal aerial lead-in](handoff_normal.gif) · [Reduced-motion lead-in](handoff_reduced.gif) ·
[Exact endpoint comparison](handoff_boundary_board.png)

The additional [handoff capture](handoff_capture.json) starts each mode with one
initial station at `aerial_descent` time 4.3 seconds, just before the canopy
transition. Production updates of at most 0.02 seconds then run continuously to
`gate_approach` time 0.2 seconds. Each GIF contains 99 samples at 50 ms exposure;
these show the visible incoming cycle, canopy occlusion, camera descent and
first ground steps without changing artwork, roots or per-frame selection.

Separate labelled boundary diagnostics initially station the exact aerial
endpoint and ground approach start in independent disposable scene instances.
Their production scene plates have zero differing RGB pixels in both normal
and reduced-motion modes. Those four stills establish the endpoint registration;
they are not presented as sequential played updates or as the continuous GIF.
The incoming eight-pose cycle excludes the later stopping anticipation.

## Validation and reproduction

All ten capture lifecycle checks pass: pause and focus freeze action/root/camera,
drawing stays pure, duplicate cues neither replay nor reset the stop, greeting
clears temporary action ownership, long reading does not restart it, Skip clears
without rewards, the same cue can restart after cleanup, and Gallery closure
clears the child. Companion journey-triggered loader and scene tests cover the
live selection and unchanged generic travel; native integration tests protect
the ordinary actor and save/scene ownership boundaries. The final targeted suite
passes all 104 tests across `test_iselin_walk_stop`, `test_regent_arrival_staging`,
`test_iselin_cinematic_foundation`, `test_iselin_replacement`,
`test_regent_arrival`, `test_regent_crossroads_gameplay`, `test_regent_aerial`
and `test_iselin_native_integration`.

```sh
python tools/build_regent_iselin.py --check
python tools/export_iselin_gate_detail.py --check
python tools/capture_iselin_walk_stop.py --check-mechanics \
  --out /tmp/iselin-detailed-gate-live
python tools/capture_iselin_gate_handoff.py --out /tmp/iselin-gate-handoff
```

The optional `--approved-capture /path/to/capture.json` repeats the selected-frame,
root and camera comparison when the original approved timed review is available.
Default output goes to `/tmp`; existing approval captures are not overwritten.
The [source pack](../../../assets/source/characters/iselin/cinematic_gate_left/README.md)
records complete generated masters, registration, protected identity pixels and
selected cells. General authoring rules remain in the
[sprite and animation standard](../../SPRITE_ANIMATION_STANDARD.md).
