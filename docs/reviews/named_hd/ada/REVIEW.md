# Ada native replacement candidate

## Identity and scope

Canonical ID `ada`, age 7, original home `home_b`. Retains dark chin-length bob, blue eyes, blue dress and cream collar. Native visible idle height is 48 artwork pixels, exactly twice the legacy height. The existing 72×72 dialogue portrait is retained byte-exact, not regenerated. Original sprite/palette/character/portrait references and SHA-256 provenance are under `assets/source/characters/named_hd/ada/reference` and `provenance.json`.

Four native idle views and four eight-pose walks only. ResidentPose uses idles/walks; no Ada/Pippa run or festival activity consumer was found. No run or invented gesture bank is included. No legacy file, identity record, map, shared loader, dialogue, collision or scene binding was changed in this art package.

## Construction and provenance

New native heads, sleeves, hands, dress torso/hem and target color treatment are explicitly drawn from integer-coordinate contours. Legacy sprite pixels were not enlarged into these outputs. Approved child_girl_05 foot/leg contour coordinates are retained as compatible native-scale motion guides, not passed off as newly invented coordinates. No guide image pixels are composited. Guide sources at commit `7dfa732ea1abe9c62cd7860f453f9b923a20a4af` and exact hashes are recorded in `guide_provenance.json`. This reuse is motion guidance only, not a roster identity substitution. Profile motion coordinates are reflected with phase adjustment, while the directional target head/hair is authored separately.

Editable inputs are `author_head.py`, `author_body.py`, and `pose_drawings.json`; flattened native masters and runtime exports are separate. The builder is reproducible and requires no generator or outside downloads.

## Geometry and review artifacts

- Artwork canvas 48×72, density 2; logical frame 24×36.
- Fixed art draw anchor [24,60], foot registration [24,68]. These preserve the named actor's original logical [12,30] and [12,34], not the generic roster foot anchor.
- Eight distinct frames per direction, 70 ms each, 560 ms cycle.
- `idles_native.png` and `idles_4x.png` show the new four-view bank.
- Each direction provides legacy/new-idle/eight-pose comparisons, labeled phases, native/normal/slow GIFs, 7–8–1–2 seam and `landmarks.json`.
- Landmark values measure visible crown, neck, hem and sole; belt is null because the design has no belt. Knees are concealed by the dress, and profile foot overlaps are explicitly noted rather than counted as missing feet.

All four directional static comparison sheets inspected for identity, contour continuity, frame progression and head/cloth registration. Continuous playback and final independent visual approval remain the integrator's review gate. Files are candidates, not an assertion of user approval.

## Verification and integration handoff

Eight ID-local unittest checks pass: geometry/identity; exact portrait; idle height and alpha; walk count/anchors/native strips/unique frames; visible sole landmarks; GIF timing; absence of unsupported motions; source hashes and reproducible export. The test suite rebuilds and compares output bytes.

`integration_contract.json` captures the original home actor, position/probe/anchors and the classroom ResidentPose ownership. Live home/classroom capture and borrow/restore checks have **not** been run here: root owns the shared binding work. Preserve the original actor's collision/probe and canonical identity; use this bank for both home and the borrowed classroom actor. Do not present these isolated art proofs as live integration evidence.
