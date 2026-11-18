# Well examination and local sound

PR5 adds repeatable examination and sound to the live well. The interaction
uses the existing dialogue UI and snapshot-based idle/working/filled text. It
reads the mechanism rather than reserving it or changing water/ownership. While
reading this inspection, the gardener and mechanism pause together and resume
the same operation when the text closes.

The sound controller observes the actual attachment, water contact, emergence
and detachment cues. Current winding and filling produce restrained loops;
finite contacts occur once. Pouring follows the visible stream at the gardener's
held pail. Finite cues missed while distant, muted or in another scene are
discarded; entering range does not play the old contact. Cues older than 125 ms
are also discarded. Eligible current loops can restart after returning.

## Short audible range

Fixed well sounds use ground center `[528,864]`. Garden pouring follows the
gardener carrying the pail with the same short range, so distant work is not heard
from the well square. The listener is the player's feet in logical world units;
camera movement and display scaling do not alter volume.

Relative volume is full through 32 units, then `((80-distance)/48)^3`, and exactly
zero at or beyond 80 units. Source gain and the effects setting multiply this
value. Existing regional sounds keep their wider smooth attenuation.

| Distance from source | Relative gain |
| --- | --- |
| 32 | 100% |
| 36, the close west well station | 77.03% |
| 48 | 29.63% |
| 56 | 12.50% |
| 64 | 3.70% |
| 72 | 0.46% |
| 80 or farther | 0% |

An active loop stops at the exact 80-unit boundary. A stopped loop must enter
12 units inside that boundary before starting, preventing repeated starts at
its faint edge. Effects mute, menus, focus loss, examination, combat, title and
interior/remote scenes release owned voices. Channel identity checks protect
other sound owners; the controller does not steal channels or alter music.

## Reproduce the review

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python tools/review_well_feedback.py
```

The helper uses a normal `Game`, temporary saves/settings, actual updates and
native 960×640 dialogue rendering. [Idle](examine_idle.png) and
[working](examine_working.png) examinations are captured through the real
interaction entry point. The signatures in [observations](observations.json)
confirm that reading changes neither the pail nor the operation.

[Well feedback](well_feedback.wav) reconstructs the production controller's
accepted start/gain/stop stream. Its listener begins at the reachable west rim,
walks away and returns through the short range, and exercises pause, focus loss,
mute, an interior visit and a return after completion. A separate labelled
garden-pour excerpt follows the same actual gardener routine; ordinary travel
between the well and garden is omitted from the montage. Player setup and the
diagnostic door transfer are explicit fixtures. The gardener is never teleported,
advanced independently or supplied synthetic station readiness.

[Source materials](materials.wav) is a separate source-bank diagnostic: six
original materials in bank order, at a fixed .34 gain with 150 ms silence
between them. It is not presented as gameplay or distance-adjusted playback.

The SDL dummy device provides no hardware loopback. Fake channel leases replace
only output hardware; production scheduling, attenuation and cue expiry remain
active. The recorder uses the current mixer sample rate, and verifies each
recorded mono source against one channel of the actual `Sound` PCM. It adds no
events, soundtrack, normalization, compression or limiting. Exact silent
intervals, gain traces, unique finite cue keys, source hashes and artifact hashes
are retained in the observations. Map, routine and collision files are checked
before and after capture.

## Measured review

The accepted-stream montage is **26.667 seconds**, 44.1 kHz mono signed-16-bit
PCM, with a **−29.47 dBFS peak** and no clipping. Its 800 recorded Game updates
include four unique finite starts: attachment, emergence droplets, detachment
and the first garden pour. The splash is discarded during the out-of-range
interval and is not replayed on return. The two physical loops restart only
while their current phase remains eligible.

All eight labelled silence intervals were checked sample-by-sample for exact
zero: idle/working examination, beyond 80 units, pause, focus loss, mute,
interior and return after completed work. The interior excerpt occurs after
retrieval; active-work scene-exit behavior is additionally covered by gameplay
tests. The material montage is 5.870 seconds and includes all six original
source sounds, separately from these accepted gameplay cues.

Nine runtime/tool/text source hashes, three map/routine/collision hashes and
four WAV/PNG artifact hashes match the final capture. Both native examination
screenshots were inspected for readable text, current character identity and
well/actor depth. The report retains all seven mechanism events, the actual
per-frame source positions/gains and the two unchanged examination signatures.

Numerical/stream review and native screenshot inspection do not establish
perceptual material identity on speakers. No hardware listening approval is
claimed. The source and WAVs remain available for that review.
