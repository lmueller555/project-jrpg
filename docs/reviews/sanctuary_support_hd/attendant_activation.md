# Sanctuary attendant native activation and mixed arrival review

The runner now uses adult_woman_01's four idles/eight-frame directional walks and
matching portrait. Her separately staged carry/place dependency is activated
only for this actor. All poses/props retain world anchors and ownership cues.
Carry and ordinary gait both use8×70ms=560ms. No story routes, speeds, positions,
character plot identities or well/gardener behavior is changed.

Native carrying retains cloth in front of front/profile bodies and hidden behind
rear body. Placement naturally bends knees, releases at700ms and recovers empty
by1200ms. Initial generated linen was visibly undersized compared with the world
bundle; the source was redrawn larger before acceptance. The deposited world
linen is unchanged, with a small forward/down snap onto its existing support.
Foot registration follows actual boot bottom rather than changing crouched-body
bounds, so bending does not drag the planted boots to fit a hand coordinate.

Actual mixed Sanctuary arrival ran all five replacements together: caretaker,
worker A, worker B, lookout and attendant. Completed after359100ms updates.
Captured carrying,600ms pre-release,700ms post-release and delivered states at
960×640 through production World.draw. At600ms a one-second paused update held
the action clock; at700ms carrying became false and the world-owned linen became
eligible exactly once. Source poses7–11 have no held linen. Worker care and rope
opening completed in that same run. See arrival_mixed_*.png and observation JSON.

This sparse package was overlaid into the full reference checkout for gameplay
capture; no other actor/scene geometry was rewritten. Native mixed rescue was
independently reviewed from the rescue-worker lane's production capture:
`rescue_mixed_caretaker_receives.png`.
Distinct seated dark-haired worker and standing silver-haired caretaker coexist
at coherent scale and spacing. That lane reports18 rescue lifecycle tests plus
6worker/caretaker focused tests passing on latest4309466e overlay.

Local focused tests cover native loaders, both carry states/directions, exact
release/completion timing, restored completed ownership and hard alpha.
Reproduce the arrival capture with `python tools/capture_sanctuary_support_hd.py`;
sparse packages may set SANCTUARY_REFERENCE_ROOT to a full checkout.

Whole merged-tree arrival Gallery/save/focus/reduced-motion suites are still
required for aggregate acceptance; this is not a claim those suites ran here.
