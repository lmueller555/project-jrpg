# Caelan rear run — artwork review

Status: user-approved artwork, accepted for merge into main. Gameplay integration
remains deferred.
The live registry, existing directional idles and walks, legacy runs and approved
HD front run remain unchanged.

- [Normal/half-speed animation and approved rear idle](preview.gif)
- [Numbered full-body frame sheet](frames.png)
- [Native frames, sources and phase metadata](../../../assets/characters/caelan/review_hd/run_back/animation.json)

## Contract

Sixteen complete rear-facing drawings at 25 ms each preserve the 400 ms full
two-step run cadence. Density is 2 artwork pixels per logical world unit.
As with the approved front run, the padded canvas is 48×76 artwork / 24×38
logical, draw anchor [24,64], foot reference [24,72]. The four extra transparent
vertical pixels allow complete poses at the approved sampling density rather
than shrinking the character. Draw and foot references shift together relative
to the idle. The preview aligns draw anchors and shows native-size examples.

Anatomical right is viewer right in this rear view. The single left-hip pouch
stays viewer left. Each arm counters its same-side leg, including when a forward
arm passes behind the torso. Bent elbows, alternating soles/heel recovery,
restrained hair and tabard motion, and two flight intervals distinguish the
run from the approved walk. No costume mirroring is used.

Visual support boundaries differ slightly between the two strides:

| Frames | Ground support / flight |
| --- | --- |
| 1–4 | Right contact, compression, support and late support |
| 5 | Right toe-off |
| 6–8 | Flight and approach to left landing |
| 9–11 | Left contact, compression and support |
| 12 | Left toe-off |
| 13–16 | Release, flight and approach to right landing |

Metadata follows these selected drawings rather than copying file-number labels
from the initial profile template. Frame 16 continues into frame 1 without a
duplicate endpoint.

## Sources and reproduction

Follow the [global visual art standard](../../VISUAL_ART_STANDARD.md#running-animations).
Rebuild with `python tools/export_caelan_back_run_hd.py` with Pillow installed.

Sources are in `assets/source/characters/caelan/run_back_hd_review/`.
`idle_reference.png` is a technical crop of the approved rear idle master.
`keys.png` establishes contacts and flight; `A.png`–`D.png` retain the initial
four-pose batches. Complete replacement drawings are retained in
`passing_correction.png`, `flight_transition.png`, `recovery_right.png`,
`recovery_left.png` and `early_flight_left.png`. Superseded cells remain source
history; only the manifest's selected source cells are current.

`provenance.json` records original generated-image locations, source hashes and
each batch's purpose. `registration.json` records selected cells, source bounds,
cranial bounds, nape/belt references, uniform scale, whole-body translations,
timing, support and boot-review windows. `protected_references.json` protects
175 pre-existing files, including the approved front run and its preview.

Every creative pose is a complete image-generation drawing against the approved
rear design. Technical export uses connected alpha extraction, uniform .124
nearest-neighbor sampling, cranial horizontal registration, small whole-body
vertical registration offsets, the existing Caelan material palette and inside
outline pass. Background fringe in the initial B source has low alpha and is
excluded by extraction. There are no detached-limb transforms, independently
timed body strips, pose rigs, idle warps or runtime bob.

## Review and validation

Inspected both arm and leg chains, contacts, flight, batch joins and 16 → 1 at
native resolution and on the enlarged numbered sheet. Initial arm reversal and
abrupt heel recovery prompted complete-pose revisions. The selected recovery
poses distribute heel rise and lower the approaching boots before contact.
One passing-correction cell changed the support-leg identity and was rejected.

The exported crown ranges from 2 to 4 artwork pixels, with at most 2 pixels of
adjacent change. Audited visible lower-boot windows are recorded in
`boot_review.json`: maximum adjacent silhouette-span changes, including the
loop seam, are 8 pixels left and 6 right. These measure projected boot silhouettes,
not hidden ankle joints; rear-view depth and boot rotation affect them. They
are local continuity observations, not a universal gait test or proof of
world-foot locking.

Export checks pass for 16 unique hard-alpha RGBA frames, transparent margins,
exact spritesheet reconstruction, selected-source hashes, 175 protected files,
phase ordering, crown continuity and the 400 ms cycle. The saved GIF has 32
alternating 20/30 ms delays totaling 800 ms: two normal cycles and one half-speed
cycle. Exact PNGs remain authoritative for color and transparency.

The existing directional walk regression suites pass (25 tests):
`PYTHONPATH=.:tests SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m unittest test_caelan_right_walk_hd test_caelan_left_walk_hd test_caelan_front_back_walk_hd`.

Travel through scenery and runtime loading of the padded bank are deferred to
integration after artwork approval. Gameplay speed, collision and live actor
selection are unchanged by this review package.
