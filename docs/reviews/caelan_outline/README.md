# Caelan overworld contour review

Caelan now uses a crisp, warm near-black inner contour comparable to Mira's
existing overworld edging. The one-native-pixel pass changes boundary colors
inside the existing alpha silhouette; it preserves canvas dimensions, ground
registration, clear gaps and interior shading. Supported bright facial and hand
edge highlights remain readable. The exact policy is recorded in the shared
builder metadata.

- [Before / after / Mira comparison](comparison.png): four directions at six
  times enlargement, plus native-size samples. Before comes from the pre-outline
  main commit `6e1a61bc`; Mira is the current reference with her own unchanged
  canvas and registration.
- [Animated travel](travel.gif): actual `Player.sprite()` selection at 20 ms
  intervals over the shared 2,800 ms gait cycle. Walk remains 140 ms per pose;
  run remains 100 ms. [All 36 travel frames](native_contact_sheet.png) retain
  constant nearest-neighbor enlargement.
- [Town](town.png) and [cave](cave.png): production scenery and lighting with a
  staged current Mira actor, including four-times crops of the same native frame.
- [World-pose samples](actions.png) and [production interactions](interactions.png):
  breakfast, sitting, sack carrying, handover, tools, and lantern handling.
- [Rescue freeing](rescue_free_worker.png), [treatment](rescue_treatment.png),
  [assisted standing](rescue_assisted_stand.png), and
  [ordinary walking at Greenwell](rescue_greenwell_walk.png) use the production
  rescue controller and renderer with explicitly seeded prerequisites/victory.

The comparisons were inspected for readable front/profile faces, retained
clothing detail, consistent outline weight, open leg/arm gaps and the town/cave
lighting difference. Travel frames were checked for contour consistency across
contact and flight poses. The actual interaction samples were checked for
sack depth, hand/tool intent, lantern ownership, and rescue body registration.
These pictured phases do not certify all unrelated scene staging.

All capture fixtures disable disk persistence. The travel fixture verifies its
quest/inventory/resource signature unchanged. Household prerequisites and rescue
victory facts are seeded; these captures do not claim a played fight or a full
quest walkthrough. PNGs are authoritative for colors and detail; the travel GIF
uses a shared review palette. `evidence.json` fingerprints inputs and outputs;
`validation.json` records the new tests and reference measurements.

The retained closed-eye pillow head and independently authored larger
cinematic/combat banks are outside this contour propagation. Historical art and
approval records remain preserved; current output is marked review.

Reproduce with:

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python tools/capture_caelan_outline.py
PYTHONPATH=tests python -m unittest test_caelan_outline
```
