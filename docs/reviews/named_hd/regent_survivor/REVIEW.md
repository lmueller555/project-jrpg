# Crown worker survivor native overworld base candidate

Canonical ID `regent_survivor`. Preserves gray swept hair, bluegray short-sleeve shirt, brown trousers, forehead dressing, dirt and guarded wrapped anatomical left forearm. That arm replaces the ordinary swinging arm, not an extra overlay. Left-wrap identity is kept through all views. Injury cycle preserves840ms total using eight distinct frames and70/140/140/70ms per half, not a sped-up generic run.

Four new48×72 idles, four8-frame walk banks, density2. Original24×36 logical canvas, draw[12,30], foot[12,34] and probe/positions unchanged. Visible idle height66 native pixels; cycle840ms. Original portrait byte-exact. No run bank: StoryActor currently selects only idle/walk for this actor, including emergency travel.

Separate native author_head.py, author_body.py, motion_contours.json and arm_contours.json reconstruct complete target poses. Compatible approved shopkeeper_01 leg/foot contour coordinates retained at native scale, no source pixels. Arm contour studies deliberately shared with this task's Page drawings, then short-sleeve/bare-forearm geometry redrawn; not represented as independently approved motion. Target shirt, trousers, hair and survivor wrap are not recolored raster substitutes. Original references and hashes in reference/provenance.json; guide provenance identifies approved source bank. Native masters separated from runtime exports.

Each direction has source/new-idle/8pose sheet, normal/native/slow GIF, numbered/seam review and landmark records. Original crown and fixed foot registration maintained; hidden belt/hip or far limb overlap not treated as missing anatomy. Static sheets inspected. Final independent motion review and live scene evidence still pending.

Seven ID-local tests pass, including whole-bank reproducibility, portrait bytes, geometry/alpha,8unique frames, exact strip cells and cadence. Commands: `python tools/build_named_regent_survivor_hd.py` and `python -m unittest discover -s tests`.

The Page stage carries shared ID-specific optional StoryActor loading for these three royal roles. Direct scene consumers of idles/walks also receive native images, while legacy scene pose ownership and timers remain unchanged. Missing banks preserve old behavior. Root must merge/test on exact main and capture live town/dining/emergency transitions. Production evidence from the frozen baseline is supplied under production/. Seated/reading/alarm/rest activity banks are separate and not yet replaced by this base candidate. Existing cinematic scene art remains untouched pending camera-quality review.

## Completed production QA and activation packaging

See production/README.md and actual Game.draw images/GIFs. The earlier sparse-only status above is superseded by this production QA. The replacement PR includes this ID’s explicit activation.json and requires BOTH its base and separately staged activity bank. Shared consumers are supplied only by Page replacement. Activity PRs remain distinct, dormant asset/source/test-only packages. Do not merge any package until the entire reviewed activation set is ready.
