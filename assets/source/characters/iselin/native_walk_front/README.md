# Native Iselin front-walk source

Status: front walk approved and integrated through the canonical native
Iselin actor. The complete approved frame PNGs and authored sources remain
unchanged. Scene-specific presentation is maintained by the native scene builder.

`keys.png` contains four complete contact/passing studies created with
`image_gen.imagegen` from the approved native front idle and cast walk
references. The two contact-reference PNGs retain whole cells extracted from
that sheet. `batch_1.png` through `batch_4.png` contain four complete generated
drawings each, in final chronological source order. Every moving pose was
authored as a complete figure, including both arms and both legs. No detached
limb rig, limb rotation or procedural anatomy generator constructs this cycle.

The character retains white hair, blue/silver royal clothing, the mantle on
anatomical right and the forward braid on anatomical left. Each arm counters
the same-side leg; movement is foreshortened in the front view. The four
batches cover contact/recovery, passing/reach, opposite contact/recovery and
opposite passing/reach. The full two-step cycle remains 16×35 ms = 560 ms.

`tools/export_iselin_native_front_walk.py` hardens alpha at 220, extracts the
connected complete figure and registers whole source cells. Per-strip density
comes from audited crown/waist landmarks, never the lowest opaque boot or an
individual pose's height. A fixed source cell size within each strip avoids
silhouette-dependent changes to rounded horizontal sampling. Registration and
source/output hashes are retained in `registration.json`.

The source strips still changed head/hair proportions at their joins. Following
the central animation standard's documented regional-preservation provision,
the exporter restores the already approved front idle's rows 0–11 after the
complete pose is exported. This stationary head/face region stays pixel-exact
throughout the loop. The neck boundary, braid tail, torso, arms, garment and
legs below row 12 remain from the authored complete drawings. No moving limb
is translated, stretched or assembled. Sources are retained unchanged.

Exports use 24×36 RGBA frames, one artwork pixel per world pixel, draw anchor
`[12,30]`, foot anchor `[12,34]` and the existing 8×4 collision probe. The review
actor uses the existing sheet-based loader with explicit frame durations; it
does not require a runtime loader change or register an HD override. Approved
native idles are included only in its review sheet for start/stop inspection.

Reproduction and actual renderer/movement evidence are documented in
`docs/reviews/iselin_native_front_walk/README.md`. Authoring rules remain in
`docs/SPRITE_ANIMATION_STANDARD.md`; this file records asset-specific facts.
