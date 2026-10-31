# Purposeful wildlife review

[Watch the complete actual-game review](purposeful_wildlife.mp4) — **2:58**, 9.5 MB.
The five chapters retain normal playback speed. [Capture summary](capture_summary.json)
and the individual reports below contain the measured timing and accepted
audio events. [Media and source verification](verification.json) confirms all
104 inputs match the final files, all six videos decode, and all 24 native/window
still pairs have the expected dimensions.

This evidence was regenerated after merging main's Gallery integration
`e80c3534` into the wildlife branch (merge `4e86b720`). The title Gallery now has
26 entries, including **A Familiar Visitor**, which replays the finite sheep and
basket visit. This compilation records ordinary regional gameplay; the
[Gallery review](../gallery/README.md) separately documents the new entry and
its [production pat-contact preview](../gallery/regional_sheep_basket_visit.png).
The per-clip input hashes include the merged `main.py`.

The capture uses the actual `Game.update` and `Game.draw`: 30 simulation updates
and 15 video frames per second, normal regional zoom, a 480×320 native canvas
and its ordinary 960×640 window. PNG pairs preserve both views. No animal,
worker, basket, pose, route step, timer or contact is assigned by the capture.

The temporary journey seeds completed predecessor quests. Garden work and its
optional care conversation run through production code before the sheep clip;
the gardener then walks her complete pasture visit in production. Initial
Caelan placements and cuts between separate sites are explicit review fixtures.

| Compilation time | Chapter | Production behavior | Evidence |
| --- | --- | --- | --- |
| 0:00–1:08 | Sheep and gardener | Grazing, full trip from garden to pasture, gathering, basket inspection, pat, basket retrieval, full return | [Video](sheep_visit.mp4), [report](sheep_visit_report.json) |
| 1:08–1:37 | Farm bird | Grain pecking, approach on foot, scatter, clear cooldown, completed landing | [Video](bird_grain_scatter_return.mp4), [report](bird_grain_scatter_return_report.json) |
| 1:37–1:53 | Butterfly | Short flights among petals of the actual authored southern flower patch, with settled pauses | [Video](butterfly_flowers.mp4), [report](butterfly_flowers_report.json) |
| 1:53–2:33 | Farm cat | Sleep, stretch, checked ground route, second resting place, return | [Video](cat_sun_and_rest.mp4), [report](cat_sun_and_rest_report.json) |
| 2:33–2:58 | Audible distance | Walk from far to near the river, beyond cutoff, back again, mute, map pause | [Video](audible_distance.mp4), [report](audible_distance_report.json) |

Each butterfly remains at one authored flower patch; it does not commute between
separate clusters. The cat and butterflies have no added vocal or wing loops.

Native contact/pose stills: [sheep pat](sheep_pat_contact_native.png),
[basket retrieved](sheep_basket_retrieved_native.png),
[bird perched](bird_grain_scatter_return_bird_perched_native.png),
[return flight](bird_grain_scatter_return_bird_return_flight_native.png),
[bird back on grain](bird_grain_scatter_return_bird_returned_to_grain_native.png),
[butterfly flutter](butterfly_flowers_butterfly_flutter_native.png),
[settled butterfly](butterfly_flowers_butterfly_settle_native.png), and
[cat stretch](cat_sun_and_rest_cat_stretch_peak_native.png).
Each has an ordinary 2× window companion with `_native` removed from its name.

The sheep clip saves during the basket investigation, shows the title, and uses
the production Continue path. Assertions compare the complete wildlife state,
the gardener's exact feet, and the exact basket position before and after.
The [before](sheep_basket_before_continue_native.png) and
[after](sheep_basket_after_continue_native.png) stills show the preserved scene.
The later pat and basket retrieval then occur naturally. No animal or gardener
is relocated while the clip runs.

The clip reports record actor poses and positions, vignette and basket state,
accepted sound events, listener/source positions and gains, cache measurements,
and hashes of the 104 input code/art files at process start. Short wildlife cues
remain finite; the continuous river bed demonstrates audible attenuation during
a complete traversal. The bird watcher retreats south of both the flight path
and the grain, allowing an actual safe landing. At the retreat, the bird folds
its wings and holds a grounded pose. Return travel uses changing flight frames
until the bird reaches the grain and resumes pecking.

The sheep contact produces exactly one accepted cue at **37.63s** in its clip
(gain `.0742`). The bird produces one scatter cue at **8.47s** (gain `.2305`) and
one completed-landing chirp at **18.30s** (gain `.1033`). Those gains include the
actual listener distance. The sheep report ends with the visit complete and the
single empty basket home. All reports retain the same nine-animal roster.

Audio uses the existing regional recorder. SDL's dummy driver has no hardware
loopback, so accepted production start/gain/stop events drive the same generated
48kHz mono PCM offline. Channel stand-ins replace only the output device. No
normalization, editorial sound, substitute soundtrack or invented event is
added. Music is muted for review. Technical waveform and event evidence does
not establish subjective material identity or listening approval.

The distance clip checks full river gain of `.55` near the bank and released
river ownership beyond the hard cutoff. The two-second mute and map-pause
intervals are checked sample by sample for exact zero before AAC encoding;
the wildlife state is unchanged during map pause. AAC may ring very briefly at
boundaries. Raw peak levels are −28.49 dBFS (sheep), −18.65 (bird), −25.91
(butterfly), −24.05 (cat), and −18.87 (distance), including nearby ordinary
regional work/ambient effects. All remain below full scale without limiting.

Final controller SHA-256:
`dc2ce585ae4ccb129dce8a3d99d7be285423b59fcd6b5d594242faafec4ae2bb`.

Reproduce with:

```sh
python tools/capture_purposeful_wildlife.py
```

The tool requires pygame, numpy, and FFmpeg. Captures run serially because the
shared audio recorder uses fixed intermediate filenames. Intermediate WAVs are
removed after muxing to avoid duplicating each video's soundtrack.
