# Veinhold motion continuity correction

The selected drawings, 301-frame native bake and independent chronological
frame review are complete. Final reproduction, test and Gallery results are
recorded in the validation table below.

This corrects the remaining motion defects after
[PR #663](https://github.com/lmueller555/project-jrpg/pull/663), whose merged
baseline is 4719ce33. The [previous review](../veinhold_running_polish/README.md)
and its proof images remain historical evidence.

## Artwork and production review

The correction supplies 15 Lucan drawings, 22 Iselin drawings and 44 Crown
soldier drawings; four Crown poses are retained. It repairs Lucan's held/rushed
leg exchanges and second-half snap, Iselin's gait and hair/cloth loop, and
additional Crown recovery and hand discontinuities found during review.
Palette refinements preserve the existing nighttime presentation.

Every actor retains 48 complete frontal drawings over 800 ms. The 60 FPS
presentation, five-second reveal, party formation, camera and Gallery entries
are unchanged. Complete image-authored figures own the anatomy and material
movement; export and baking use whole-figure sampling and registration.

Independent QA accepted every chronological production frame 120–167, covering
all 48 poses, plus entry/tilt frames 0, 30, 60, 75, 90 and 105, palette frames
110–114, braid frames 134–138 and the terminal 299→300 transition. The inspection
found connected limbs, visible arm pumps, stable bodies/equipment, coherent
hair/cloth and consistent nighttime palettes, with no concrete blocker.
See the [review record](independent_review/review.json) and
[accepted drawing hashes](independent_review/accepted_drawing_hashes.json).

## Pixel checks and retained failures

The three scoped instruments measure finished artwork:

- [Motion](../../../tools/audit_prologue_motion.py): reviewed boot-contour
  windows, early recovery progress, regional hair/cloth contours, whole-export
  registration and a fixed torso-model reference.
- [Hands](../../../tools/audit_prologue_hands.py): actual warm skin/glove
  components, complete chronological coverage, a minimum 40-pixel full-cycle
  pump and a conservative 60-pixel gross component-step guard. Shifts above
  40 pixels also produce review diagnostics. Hidden shield wrists are
  explicitly unmeasured.
- [Braid](../../../tools/audit_prologue_braid.py): actual cool, light RGB pixels
  in reviewed exported braid regions. This detects internal movement over an
  opaque coat that an alpha silhouette cannot reveal.

Source SHA, cell crop, measured neck/belt positions, density and origin are
bound to the [registration observations](../../../tests/fixtures/prologue_motion/registration_observations.json).
Glove-window approvals additionally bind the cropped RGBA pixels; braid approvals
bind the actual exported RGBA view and exported neck registration. A geometry
change cannot reuse an old approval by compensating metadata alone.

The [motion contract](../../../tests/fixtures/prologue_motion/contract.json)
retains a 65-pixel adjacent boot bound, 20/30-pixel exported neck/belt bounds and
fixed torso references with a ±10% allowance. Regional contour defaults remain
28 pixels for hair, 30 for the shawl and 35 for the free coat.
Reviewed foot windows distinguish crossing limbs without omitting their joins.

The final identity review inspected all 288 boot endpoints and all 192 visible
hand components across the three complete banks. Five broad foot windows had
selected an opposite calf/greave; source-specific windows now select the actual
soles. Two Crown hand regions selected sword fittings below the gripping fist;
their corrected windows select leather fingers/knuckles. Separate real-pixel
regressions retain these false matches. Crown frame 40's glove measurement was
refined from a supported outer edge to an inner finger crease; the old edge was
not a sword-fitting defect. See the final overlays and hash-bound observations.

The actual rejected paintings remain hash-bound negative fixtures:

| Retained defect | Measured failure |
| --- | --- |
| Lucan boot regions, 38→39 | +141.12 and −182.70 artwork pixels against the 65-pixel bound. |
| Crown recovery boot, 10→11 and 11→12 | −84.60 and +70.20 pixels against the same bound. |
| Iselin shawl/free coat, 47→00 | 33.157 / 39.640 pixels against defaults of 30 / 35. |
| Lucan 35→36 and Iselin 02→03 visible hands | Approximately 72 / 79 component-centroid pixels against the 60-pixel gross-step bound. |
| Retained internal braid joins | Actual RGB region jumps fail while ordinary real neighbors remain controls. |

The [motion](../../../tests/test_prologue_motion.py),
[hand](../../../tests/test_prologue_hands.py) and
[braid](../../../tests/test_prologue_braid.py) tests cover those real failures,
repeated/reordered/frozen paintings, invented guide labels, missing coverage and
changed pixels/registration. Braid RGB removal is tested with every alpha byte
unchanged. Reviewed statistical cases also lose acceptance if their source,
crop, origin, rendered pixels, metric definition or observed-value band changes.
The Crown frame 30 forearm dip was found and corrected visually while below the
gross hand bound; automatic detection of that defect is not claimed.

## Reviewed statistical diagnostics

The unchanged 0.70 three-tick concentration trigger is diagnostic. One coherent
Lucan recovery measured 72.2%, approximately 4.56 artwork pixels beyond it.
Independent QA found no defensible visual boundary at that difference, given
toe rotation and changing distal contours. The rejected art still fails the
hard snap and early-hold checks.

Two final shawl statistics exceed their default 30-pixel bound:

| Exact reviewed transition | Observed statistic | Maximum reviewed value |
| --- | ---: | ---: |
| Iselin 13→14 | 45.134 | 46.134 |
| Iselin 14→15 | 33.187 | 34.187 |

Root and independent source/native-frame review accepted continuous cloth
action. The palette refinements changed same-frame hair/shawl/coat contours by
5 / 4.12 / 4.47 pixels for frame 13 and 1 / 1 / 1 for frame 14. Small raster
boundary changes alter the population behind the cross-frame 90th-percentile
statistic; the drawings show no new cloth reset.

The final braid bends likewise have explicit reviewed diagnostic cases in the
[braid contract](../../../tests/fixtures/prologue_motion/braid_contract.json):

| Exact reviewed transition | Observed statistic | Maximum reviewed value |
| --- | ---: | ---: |
| Iselin 13→14 | 73.563 | 74.563 |
| Iselin 32→33 | 68.977 | 69.977 |
| Iselin 37→38 | 71.362 | 72.362 |

All 48 contributing braid regions were independently inspected. Six windows
were narrowed to exclude embroidered cuffs; no contributor was restored to
make a statistic smaller. The default centroid bound remains 65 pixels.
A regional color centroid is not an exact tip or persistent hair particle.

The shared [review helper](../../../tools/prologue_motion_review.py) binds each
case to exact source hashes, crop/scale/origin, neck/belt registration, rendered
RGBA hashes and metric configuration. Its observed-value sampling band is at
most ±1 pixel, with a separate recorded maximum. A 2-pixel departure is rejected
by the negative control. These cases remain visible diagnostics; default bounds
and rejection of the retained bad artwork are preserved.

## Limits

The review inspected consecutive drawings and native production frames. The
available image tool cannot play video, so watched normal-speed playback is not
claimed. Generating a movie or running a paced capture does not establish that
it was watched.

Lucan's settled ground anchor is approximately y = 697, below the 960×640 crop;
Iselin's contacts are near the lower edge. Native stills therefore do not
establish world-ground foot locking. Source contacts and Foley remain useful
checks for cadence and phase.

Boot contours, hand components, braid centroids and contour-feature velocities
are scoped measurements, not persistent joints or physical material points.
Occlusion, perspective and detector identity still need review. Changed source
pixels invalidate old pixel-region approvals.

## Reproduction and validation

Run with the game's Python environment from the repository root:

~~~sh
python tools/export_prologue_faces.py --check
python tools/export_prologue_runners.py --check
python tools/build_prologue_face_environment.py --check
python tools/build_prologue_alert_audio.py --check
python tools/audit_prologue_motion.py --before --output /tmp/motion-rejected.json
python tools/audit_prologue_motion.py --output /tmp/motion-after.json --overlay /tmp/motion-windows
python tools/audit_prologue_hands.py --output /tmp/hands-after.json --overlays /tmp/hand-windows
python tools/audit_prologue_braid.py --before --output /tmp/braid-rejected.json
python tools/audit_prologue_braid.py --output /tmp/braid-after.json --overlay /tmp/braid-windows
python -m unittest tests.test_prologue_motion tests.test_prologue_hands tests.test_prologue_braid -v
python -m unittest tests.test_cinematic_perspective tests.test_cinematic_bridge_run \
  tests.test_cinematic_face_reveal tests.test_fire_veinhold_opening \
  tests.test_prologue_alert_audio tests.test_prologue_flight_audio \
  tests.test_prologue_capture tests.test_prologue_mountain_export \
  tests.test_prologue_eagle_assets tests.test_cinematic_facility \
  tests.test_cinematic_smoke tests.test_prologue_face_export
python -m unittest tests.test_gallery_catalogue tests.test_gallery_session tests.test_gallery_ui
~~~

Rejected-art audit commands are expected to exit with status 1. Their
negative-control tests pass when those actual defects are detected. Reports
and overlays retain rejected and corrected evidence separately.

| Validation | Result |
| --- | --- |
| Frozen source selection and native production inspection | Complete; hashes and independent review linked above. |
| Native performance bank | 301 inclusive 960×640 frames baked successfully; see [build log](performance_build.log). |
| Exact source/performance reproduction | All three 48-pose exports and all 301 native frames reproduce exactly; side export and audio checks also pass. |
| Retained real failures | Motion, hand and braid rejected-art commands exit 1 for the measured defects; ordinary braid controls remain accepted. |
| Final production audits | Zero hard violations in [motion](motion_after.json), [hands](hands_after.json) and [braid](braid_after.json); reviewed statistical diagnostics remain recorded. |
| New pixel-based regression suite | **35 passed**: 18 motion, 7 hand, 10 braid checks; [log](painted_motion_tests.log). |
| Existing cinematic checks | **144 passed**; [log](core_tests.log). |
| Gallery checks | **71 passed**; [log](gallery_tests.log). **250 unique tests passed** across these three suites. |
| Production Gallery captures | Both five-second reveal modes (300 frames each) and the complete 47-second film (2,820 frames) complete naturally, return to Gallery and write no persistent save/settings files. [Capture records and filmstrips](production_gallery/). |
| Captured pixel match | All 12 selected normal/reduced stills exactly match the corresponding native production frames; [record](production_gallery/native_frame_match.log). |
| Compilation and whitespace | Changed Python files compile; `git diff --check` passes. |

Capture timings use unpaced, offscreen SDL-dummy draw/update wall time, excluding
encoding and review stills. Normal reveal mean/p95 were 5.988/18.290 ms, with
19 of 300 frames above 16.667 ms; reduced motion mean/p95 were 5.408/13.766 ms,
and the complete film 7.068/12.811 ms. These figures are not a hardware playback
guarantee or a watched-video claim. The frontal cache peaks at 19,660,800 bytes
(eight native surfaces), releases on completion and loads no separate actor bank.
