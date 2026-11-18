# Iselin walking stop and standing settle

This review covers the left-facing stop at the southern arrival gate. It uses
the approved native Iselin design, eight new complete stop drawings, the existing
last walking pose, and the exact approved standing idle. General construction
and performance rules remain in the
[sprite and animation standard](../../SPRITE_ANIMATION_STANDARD.md).

## Continuous production capture

[Normal speed](normal.gif) · [Quarter speed](slow.gif) ·
[Full-shot samples](samples.png) · [Native frame board](numbered_frames.png)

The capture starts by selecting the existing `gate_approach` shot at time zero
inside a real isolated arrival Gallery child. After that single fixture setup,
the helper advances the actual `Game.update` and renders through `Game.draw`.
It does not assign action frames, switch poses or force phase transitions.
The normal/slow GIFs show the same 101 samples from approach time 0.8 through
2.8 seconds, including walking, the stop, and the actual greeting handoff.
They last 2,020 ms and 8,080 ms respectively. Each decoded GIF frame matches its
quantized source and each saved exposure is checked. Full-frame PNG samples
remain the lossless color/composition reference.

Updates are at most 20 ms, with extra subdivisions at the declared key times.
These remain ordinary delta updates; the precise subdivisions make the 1.25 s
cue and 1.95 s phase boundary inspectable without selecting an artificial frame.
The GIFs crop the production window to keep Iselin, the guard, the page, Lucan
and the road visible. The crop and times are recorded in [capture.json](capture.json).
The camera uses its original 1.5-second pan and then holds.

| Approach time | Performance | Lossless production frame |
| --- | --- | --- |
| 0.80 s | Existing walking cycle | [Walking](walking.png) |
| 1.24 s | Last pre-cue walking sample | [Before handoff](handoff_before.png) |
| 1.25 s | Exact approved frame 16; stop cue begins | [Handoff](handoff.png) |
| 1.29 s | First newly drawn contact pose | [Contact](contact.png) |
| 1.41 s | Weight transfer and arm damping | [Weight transfer](weight.png) |
| 1.53 s | Trailing foot closes as root slows | [Closing](closing.png) |
| 1.65 s | Narrow stance, diminishing secondary motion | [Settle](settle.png) |
| 1.75 s | Root reaches its unchanged destination | [Root stopped](root_stopped.png) |
| 1.83 s | Exact approved standing idle in recovery | [Idle recovery](idle_recovery.png) |
| 1.95 s | Real transition into the greeting shot | [Greeting starts](greeting_start.png) |
| 2.35 s | Greeting holds the settled idle | [Greeting](greeting.png) |
| 2.75 s | Continued reading leaves the stop complete | [Long hold](long_hold.png) |

The phase-local action clock is transient. Greeting clears the stop player and
continues with the ordinary standing pose; waiting on dialogue does not replay it.
The stop's 700 ms comprise an exact 40 ms walking handoff, eight new frames at
60 ms each, a 60 ms final hold and a 120 ms recovery into the approved idle.

## Motion and registration

The approach initially retains 24 cinematic pixels per second. At 1.25 seconds
Iselin is at `[581,375]`, with the existing walk at frame 16. Over the next
500 ms, her root decelerates linearly to zero and travels the remaining six
pixels to `[575,375]`. A further 200 ms completes the settle before greeting.
The other cast tracks retain their original timing and endpoints; hoof/wagon
audio follows the caravan's movement rather than Iselin's remaining footstep.

The [world registration board](world_contact_board.png) is a separate diagnostic
composition. It uses the actual selected whole surfaces and measured root
positions from the production capture, with one common world origin, anchor and
inspection scale. A pale fixed-world guide helps inspect the planted leading
foot while the trailing foot closes. It removes camera movement for inspection;
it is not a screenshot, a redrawn pose, or evidence of pixel-perfect contact.
No individual foot or occupied sprite bounds are used to align its cells.

The [source recipe](../../../assets/source/characters/iselin/native_stop_left/recipe.json)
and [registration record](../../../assets/source/characters/iselin/native_stop_left/registration.json)
record the generated complete drawings, common sampling/registration, palette
mapping and exported hashes. The original generated sheet is retained. Approved
head/neck rows are preserved after complete-frame registration: walking height
for the first six new drawings, then the standing reference for the last two.
The moving body remains authored complete artwork, with the deliberate small
rise into standing and restrained coat/braid follow-through. The actual scene
continues using its 80×96 camera canvas and `[40,92]` anchor.

## Historical comparison

[Before this PR](before.gif) records the unchanged pre-stop main runtime at
`e1a010069507b592020ee4addf93f0a5d545ed5e`. It uses the same initial-shot fixture,
ordinary updates, crop and sampling times, and shows the former direct walking
to standing switch at the old 1.5-second boundary. Only its normal-speed GIF is
retained; [before_capture.json](before_capture.json) records the historical
runtime/source hashes, timeline and retained artifact hash.

The current capture records its working-tree base commit and exact input hashes.
It was made before committing this PR, so the input hashes identify the reviewed
new runtime and artwork rather than claiming that the unchanged base commit
already contained this performance.

## Reproduction and checks

From the repository root with the game's Python/Pygame/Pillow environment:

```sh
python tools/build_regent_iselin.py --check
python tools/capture_iselin_walk_stop.py --check-preservation --check-mechanics \
  --out docs/reviews/iselin_walk_stop
```

Routine captures default to `/tmp/iselin-walk-stop`, preserving this review.
`--repository /path/to/checkout` can render a clearly labeled historical checkout
in a separate process; `--classification` labels its GIFs. The historical check
is opt-in so future intentional asset work does not require rewriting this
review's baseline.

The immutable [preservation baseline](preservation_baseline.json) records the
69 approved native idle/walk/portrait PNGs plus the existing arrival/aerial actor
PNGs, 220 unique files total. All match before and after capture. New stop art,
the additive action manifest, scene timing and provenance are outside this
unchanged-PNG claim.

The recorded mechanic checks cover pause and focus freeze for action/root/camera,
draw purity, duplicate cue rejection without reset, greeting cleanup, long-read
stability, Skip without quest/inventory rewards, same-cue restart after cleanup,
and Gallery-child disposal. Every parent save/settings path is temporary and the
Gallery child remains nonpersistent.

The final targeted validation comprises 238 existing regression checks, 16 new
walking-stop checks and 10 staging checks: 264 passing tests. The stop tests also
cover exact cue boundaries reached by partitioned updates and the authored frame
boundary at 1.41 seconds. The final capture's input hashes identify the same
frozen runtime used for that validation.

This evidence deliberately stations one authored shot and reviews the resulting
continuous approach/stop/greeting. It does not claim a fully played arrival,
road journey, quest, meal or battle walkthrough. Passing mechanics checks is
complemented by inspecting the native frame board, registration board and actual
scene samples for anatomy, body scale, foot progression and depth.
