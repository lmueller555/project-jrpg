# Eldenmere low-roof proportion correction

## Scope and supersession

This correction addresses #256 and is verified over #257 on main
`4f3dbed6ebfb37bbb432f08685c94dadf90baeb5` (including the civic commons and school approach). The owner rejected the remaining tall,
3D-like roof proportions and asked to return to the old 24px roof designs at
48px artwork density. #256 recovered shingle language and taper but retained
excessive roof-image height. Its depth-preservation claim is **superseded**:
collision-ground depth is not a minimum screen-space roof rise. The previous
[roof-style review](../eldenmere_roof_style/README.md) remains historical evidence,
not a construction rule or proof of this correction's validation.

The native 2× authoring path remains in use. Reference enlargement is only for
comparison, not the source of exported roof detail. Preserve the current walls,
footprints, door/facade registrations, eave elevations, viewport anchors and
gameplay, together with #254's courtyard and #255's workshop/mill yards.

## What the actual old assets measured

The pre-HD reference commit is
`7cebbd6006a1d925163ffe607443059ffff79880`. Paths below are relative to
`assets/terrain/eldenmere/`. Measurements come from the actual exported PNGs,
not source-concept canvas sizes or ground rectangles. At this legacy density,
one image pixel equals one logical world unit. At native 2×, multiply each
linear dimension by two; do not double logical placement or collision.

**Convention:** roof rise includes the ridge cap and visible eave/fascia through
its underside; eave span is the maximum opaque width of the main roof. Visible
body runs from the main roof ridge to the building foundation/threshold, excluding
chimneys, bell towers, smoke, hanging signs and detached props. The mill's porch
is excluded. Raster edge details and blended roof/structural timber boundaries
make the visually measured figures approximate. These are not claimed to be
exact masks for every textured roof pixel.

| Historic asset | Approximate roof rise / eave span (logical px) | Rise / span | Roof / visible body |
| --- | --- | --- | --- |
| `cottage/closed.png` | 47 / 120 | 39% | 54% |
| `cottage_shapes/compact/slate/closed.png` | 47 / 96 | 49% | 54% |
| `cottage_shapes/wide/slate/closed.png` | 47 / 144 | 33% | 54% |
| `workshop/closed.png` | 53 / 143 | 37% | 55% |
| `school/exterior/closed.png` | 66 / 183 | 36% | 51% |
| `sanctuary/closed.png` | 69 / 214 | 32% | 54% |
| `watermill/building.png`, main gable | 56 / 103 | 54% | 39% |

Cottage roof pixels start at y57, although its recipe's extraction slot starts
y56; the tiled plane ends around y98 and underside timber around y103. Its body
ends at y143. All three cottage widths retain the same height. Workshop ridge
starts around y71–72, with fascia through y123 and body through y167. The school
builder specifies the polygon `(31,65),(159,65),(186,123),(184,128),(8,128),(6,124)`
and ridge caps starting y63. The outlined roof layer's actual alpha bbox spans
183 pixels, wider than the polygon vertices alone. Its visible body ends y191.
The household has continuous ridge around y78, end-cap pixels around y75,
fascia through y143 and foundation through y202. The mill has a true gable
around y0–55 and main body through approximately y141, not a rectangular sheet
whose height can be substituted for ground depth.

The result is consistent: ordinary old roofs occupy roughly **half** the visible
roof-plus-wall building. Chimney/bell height and transparent canvas padding must
not inflate that measurement. The distinctive mill is not an ordinary cottage.

## Restored dimensions and retained anchors

The construction dimensions below are in logical units. “Core rise” is the
roof drawing's ridge-to-eave parameter; approximately three additional units of
visible edge/fascia complete the silhouette. Rasterized contour pixels can add
an endpoint pixel, so these are drawing parameters, not inclusive-alpha counts.

| Family | Eave span | Core rise | Retained eave elevation (local y) |
| --- | ---: | ---: | ---: |
| Compact / base / wide cottages | 96 / 120 / 144 | 44 | 105 |
| Workshop | 144 | 50 | 127 |
| School | 183 | 63 | 145 |
| Household | 214 | 66 | 153 |
| Mill processing bay | 72 | 55; front gable 47 | Existing processing-bay wall contacts |
| Mill receiving annex | 43 | 18 | Existing annex wall contacts |
| Inn | 191 | 54 | Existing facade contact |
| Item shop | 162 | 48.5 | Existing facade contact |

The cottage, workshop, school and household recover their old roof silhouette
scale above **current** facades. Their current wall heights and eave elevations
are deliberately not reverted. Consequently the corrected roof-to-total-visible-
body fractions need not exactly equal the old table: that would require altering
protected walls or doors. The mill adapts the authentic front-gable language to
its retained processing bay and smaller receiving annex rather than replacing
its modern hoist, wheel, yard or gameplay with the old whole-building asset.

Inn and item shop debuted at HD. Their pre-audit HD reference is `90d36c88`,
under `assets/terrain/eldenmere/business_exteriors_hd/buildings/`: the original
roof silhouettes measure approximately 191×57 and 162×51.5 logical units,
respectively. They are separate references, not fabricated 24px predecessors.
The new dimensions preserve those low silhouette proportions and their own
building identities.

## Attached details

Flue horizontal registration remains aligned with each retained hearth. Lower
the roof-only chimney shafts and their smoke-cap origins together to sit naturally
on the restored slopes. The mill shaft ends where it contacts the narrow right
roof return, rather than floating past it. The school bell remains supported as
its mount follows the new ridge. The household belfry and its animated visual
mount move 14 logical units down together, retaining the cadence, courtyard and
gameplay. The louvres and roof repairs remain attached; the restored eave heights
do not move door, wall or facade anchors.

## In-game comparison and verification

These are matching, unscaled crops from actual production Game captures. The
“Before (#256)” label identifies the old roof appearance: both sides retain
the latest #257 civic commons and school approach.

- [Cottage, school, Serene’s house and mill](before_after_native.png)
- [Workshop, inn and item shop](before_after_business_native.png)
- [The other six homes](before_after_homes_native.png)
- [Exact validation record](validation.json)

The paired review matched the player, camera, time, door state, and motion
setting across 192 fixtures. All 13 revised roofs were inspected; the 31
non-town views are pixel-identical. The 193 revised views include the actual
southern return. All 63 town movement checks and three Continue checks
passed. A separate production commons capture passed 24 routes, two doorway
round trips, nine Continue checks and two recoveries from older checkpoints
inside new supports; it preserved quest, party and inventory progress.

The live town map changes only four verified exterior manifest source hashes.
The ground chunks, collision, navigation, room assets, doors, settlement
placement records, and earlier courtyard/workyard/commons work remain intact.
The commons ledger regression still verifies every gameplay entry and entity.
It now validates the refreshed exterior source hash against the live file
rather than requiring old roof-art provenance to remain byte-identical.

123 focused tests passed (106 other tests and all 17 commons tests after the
narrow provenance assertion update). All relevant architecture, exterior,
business, settlement and town exporter checks passed. The full repository suite
was not run. Production evidence is from the tested art/integration commit;
the final follow-up only adds this review and updates the commons test assertion.
