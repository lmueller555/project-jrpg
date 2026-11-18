# Caretaker native reach landmark correction

Aggregate verification exposed stale legacy hand landmarks. Two actual fingertip
positions also lay slightly beyond the existing four-world-unit preferred bound:
frames3/6 had4.74/4.47-unit gaps. Source-authored near-arm corrections open the
same natural elbow slightly farther, without changing shoulder/body/feet or
moving the actor. Only their exported arm rectangles change; all outside pixels
and the other14 complete frames are byte-preserved. Source and export hashes
are recorded in assets/source/characters/sanctuary_caretaker_hd/reach_correction.json.

Guided frames3–7 now record actual logical grip/shoulder/elbow landmarks, including
half-world coordinates. Actual fingertip-to-rope gaps are3.81,2.50,3.35,2.69,4.00
world units. Grip may denote the fingertip contour, not only an interior skin
color. Both arrival and rescue retain identical source landmarks.

The existing test keeps its <=4 reach bound and rope alpha checks. It now samples
the authored native texel at2× density rather than truncating a fractional logical
coordinate into the lossy1× mirror. No assertion is weakened or removed.

Actual complete arrival replay at50ms updates captured corrected350/650ms poses
and finished after713updates. Both native screenshots show nearby rope, coherent
arm/body scale and planted feet. No timing, transfers, paths, actor positions,
rope geometry or collision changed.

Final combined verification: all53 existing arrival Gallery/state/objects/polish/
blocking/party and rescue lifecycle tests pass, plus the arrival completion test
repeated with reduced motion enabled (54/54). Ten native activity/identity tests
also pass. Each gameplay test ran in an isolated process during an exclusive
Game window. Six initial harness-only imports were corrected before the full
final clean rerun; no production assertion was skipped.

Against current main6b945799 (#558), arrival/rescue/care/rope modules and the
rescued-worker manifest are identical to the overlay. Noncaretaker registry data
is identical. All226runtime PNGs for the six migrated roles match except these
two deliberate corrections. Other story actors retain the separately reviewed
baseline; this report scopes native migration acceptance to the six support roles.
See final_combined_verification.json and final_main_input_comparison.json.
