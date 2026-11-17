# Eldenmere settlement framework — PR 1

This delivers the first of eight settlement-composition PRs: a source recipe,
semantic asset catalogue, protected-space contracts and build validation. The
[central terrain reference](../../TERRAIN_ART_STANDARD.md#eldenmere-settlement-framework)
owns maintenance guidance. The [regional guide](../../world/regions/ELDEN_VALE.md)
remains the creative authority.

## Scope and activation

The recipe describes five overlapping role envelopes: Serene's terrace,
workshop/mill, commons/households, eastern growing area and southern arrival.
They identify future work; they do not declare empty ground or collision.

There are **zero active placements and zero ground treatments**. The framework
adds no runtime module, blocking mask, scene, interaction or save state. Its
recipe rejects nonempty activation lists until a later composition PR explicitly
adds the corresponding integration. The existing town composer remains the only
writer of the live map. It produces a separate
[`settlement/manifest.json`](../../../assets/maps/eldenmere/settlement/manifest.json)
and references that report from its build manifest.

The current streets, artwork and known pending art issues are preserved. These
captures prove framework equivalence, rather than visual approval of the
existing bridges, buildings or town-antler placement. Their separate art repairs
are outside this PR.

## Contracts and catalogue

The report resolves **114 protected spaces** from current interfaces,
53 explicit source selectors, eight owned-fixture bounds and two reviewed
code-owned envelopes. Coverage includes all 13 door approaches, southern
departure/return, upstream contact, street loop, crossings, stairs, well operation
and gathering, gardener travel, Tomas's outdoor steps, workshop fittings,
Lantern/Regent/MQ02 town stations, Liam/Daisy play and Venn's gate work.

Source selectors keep evidence of the file and path that owns each shape.
Coordinates can be authored in tiles or logical units; padding is always logical.
Route tests follow the swept segments instead of blocking the whole rectangle
around an L-shaped route. Sightline checks include the standing body above its
feet. Owned well/work fixtures reserve their artwork independently of operating
contacts, preventing new dressing from overlapping those functional instances.

Mixed-scene story files are selected explicitly. Indoor family, dining, bedroom,
school/craft, upstream and cinematic coordinates are excluded where they do not
belong to the town. The two code-owned envelopes carry reviewed source hashes;
a changed owner fails validation until its geometry is reviewed again.

The catalogue contains **200 semantic records** from six maintained packs and
validates **1,151 native images** against their declared logical size and density.
It distinguishes existing bindings, candidates, source-pack approval metadata and
functional owners. Crop-bed and working-yard gaps remain recorded future work.
Generated town maps/manifests are not hashed as producer inputs, so the report
does not depend recursively on its own output.

Future placement validation checks native asset compatibility, namespaced IDs,
logical top-left registration, bounds, explicit solid footprints, movement
reservations and tall-art sightlines. It does not place any proposal or replace
the later in-game movement/visibility review.

## Review evidence

[`before.json`](before.json) retains the pre-hook witness.
[`observations.json`](observations.json) records the final comparison, production
file hashes, map-field hashes, camera fixtures and native pixel hashes.

- **926 production input files and every town-map field match the baseline.**
- **All 13 native gameplay frames match exactly**, covering seven district/cluster
  views and six water samples.
- Quest, party, inventory and dialogue flags remain unchanged in the fixture.
- A water-only crop changes by 86 / 103 native pixels at 200 / 400 ms normally;
  reduced motion changes by 0 / 0.

The screenshots use initialized production `Game` rendering at 960×640 with
fixed clear-ground camera fixtures and disposable save/settings paths. They are
not an uninterrupted quest playthrough. Gameplay regressions separately exercise
the relevant controllers and transitions.

| Area | Actual native gameplay view |
| --- | --- |
| Serene's terrace | [Courtyard](serene_terrace.png) |
| Working places | [Workshop](workshop_yard.png), [mill](mill_yard.png) |
| Civic center | [Commons](commons.png), [school](school_frontage.png) |
| Eastern terrace | [Growing area](eastern_growing_area.png) |
| Southern arrival | [Business lane and road](southern_arrival.png) |

[Protection plan](protection_plan_diagnostic.png) is a separately labelled
diagnostic overlay on the current overview. Cyan indicates movement clearance;
amber marks records that also protect sightlines. It displays source padding;
placement validation additionally accounts for standing-character height. Existing
fixtures can already occupy their own reservations: the overlay is not a claim
that every highlighted pixel is currently walkable.

## Reproduce

```sh
python tools/build_eldenmere_hd.py --check
python tools/build_eldenmere_settlement_framework.py --check
python -m unittest discover -s tests -p 'test_eldenmere_settlement_framework.py' -v
python tools/capture_eldenmere_settlement_framework.py /tmp/settlement-review \
  --baseline docs/reviews/eldenmere_settlement_framework/before.json \
  --protection-manifest assets/maps/eldenmere/settlement/manifest.json
```

Use the repository's Pygame/Pillow dependencies. Captures default to dummy SDL
drivers and never write a player's journey or settings.

Independent review caught and corrected a catalogue density-field mismatch,
missing scene validation on reviewed envelopes, and an owned-well overlap that
operating contacts alone did not cover. Focused regressions include a real
catalogued asset, L-route clearance, actor visibility, source/filter failures,
code changes, duplicate/off-map instances, current public/work interfaces,
determinism, mutation-free validation and accidental-activation rejection.

The 61-test core run passed: 14 framework tests, 18 town-integration tests,
five southern-exit regressions, eight overworld-travel tests and 16 renderer
tests. The full town exporter verifies all 842 products; the standalone framework
check also passes.

A broader 104-test household/Lantern/Regent run reports 27 errors, including
subtests, from one existing production error: `LanternRest.workshop_empty` is
missing when `lantern_quest.py` synchronizes collected-frame props. An independent
standalone reproduction confirms it without cross-suite SDL state. The affected
runtime files are identical to the base; commit `7c59a2e8` removed the
initialization while leaving its consumer. This PR does not change those
controllers or represent that broader story run as green.
