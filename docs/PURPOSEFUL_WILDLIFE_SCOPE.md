# Purposeful regional wildlife

Initially scoped on main `f6e5ed56`, including garden/orchard PR92 and regional
NPC animation PR94; integrated main `70ef6b23` with millrace recovery PR95 before
final validation.
This is a focused regional charm PR; parent owns final review and merge.

## Intent and authored places

Replace the four decorative sheep in the existing southern/eastern pens, the
western farm bird and woodland clearing bird, and the southern/orchard
butterflies with a fixed small wildlife controller. Add one farm cat (there is
no existing regional cat to replace). No new quest, named cast, town actor,
reward, produce, day/night scheduler or region-wide simulation is introduced.

Sheep graze along checked short waypoints within their existing fence lines.
After the kitchen gardener has finished the optional plant-care beat, she may
make one finite visit down the existing southern access path. The sheep gather
at the familiar worker, one noses a reachable empty wicker basket, and she
pauses to stroke it before retrieving the same basket and returning. The
harvest baskets and their turnips never move. Routes will use verified pixel
coordinates, with the gate kept available to Caelan. The gardener's work
controller remains the owner of its durable work state; any temporary actor
loan must preserve exact restoration, avoid two active motion controllers,
and never broaden its normal work routes.

Birds land beside visible spilled grain, peck, scatter when Caelan approaches,
and return only after a cooldown with the landing clear. Butterflies travel
among the petals of actual flower patches, then settle briefly. One cat sleeps at a sunny
farm doorstep, stretches and follows a checked short ground route to a second
resting place. Animals use coherent pixel silhouettes, anchored feet and
purpose-specific poses consistent with existing wildlife. No placeholder boxes.

## Runtime, ownership and sound

Use one bounded regional controller with a fixed actor roster and distance
activation. Chunk rendering never creates actors or advances behavior. Animal
motion yields to Caelan; animals do not become permanent navigation blockers.
Ground routes respect authored terrain, fences, props and worker footprints.
Pause/dialogue/travel/title suspend behavior. Save/Continue retains finite sheep
vignette progress, basket ownership, active pose/route and cooldowns without
replicating animals, resetting contacts or producing duplicate material.
Transient clocks/positions are excluded from `progress_dict` autosave dirtiness.

Quiet sheep, bird and wing cues are finite contact/state-change events. They use
the existing RegionalAudio allocator with Caelan as listener, low priority, one
wildlife family, cooldowns, hard cutoff and normal lifecycle/channel release.
No butterfly loop, perpetual bleat/chirp, culled source or controller channel.

## Acceptance and review evidence

- Verify every sheep waypoint and sampled ground segment inside the correct pen;
  validate the gardener and cat routes against production collision.
- Verify bird approach scatter, safe return cooldown, flower targets, fixed roster,
  player passage and yielded movement recovery.
- Exercise pause, dialogue, distance/chunk activation, travel and return; save and
  Continue during the sheep/basket beat with a single owner and preserved contacts.
- Verify no per-frame disk saves; no changes to quests, harvests or town companions.
- Test finite audio PCM, event/contact timing, distance cutoff, cooldowns, caps,
  low-priority behavior and release at lifecycle boundaries.
- Capture actual Game.update/draw at normal zoom and playback speed showing all
  four families and the sheep relationship. Include audible near/far traversal,
  inspect real captured frames and disclose any audio-listening limitation.
- Run focused tests and the full production suite at final exact head on latest
  main. Publish a draft PR with scope, tests, gameplay evidence and Library ID;
  coordinate with parent before any merge.

Likely files: `purposeful_wildlife.py`, minimal `garden_orchard.py` ownership hook,
`overworld_world.py`, `overworld_travel.py`, lazy-world restoration in `main.py`,
`regional_audio.py`, bounded wildlife art, dedicated tests and capture tooling.
Detailed verified route coordinates and final implementation notes follow below.

## Implemented ownership and lifecycle

`PurposefulWildlife` owns exactly nine animals for the lifetime of the regional
world. The renderer filters the eight replaced decorative IDs; chunk cache
eviction cannot construct another actor. Each nearby actor runs one short
authored route, with a 260-pixel activation limit. Sheep remain in their pens;
the cat's entire route stays separate from the gardener's walking lane. Animals
yield to Caelan but do not add player collision blockers. The grounded basket
has one small footprint and is absent from collision while being carried.

After the existing gardener reaches her completed `rest` checkpoint, wildlife
temporarily owns that actor's feet, pose and movement. Garden work skips the
borrowed actor and keeps its completed home snapshot; it still owns all its
harvested produce and plant. The wildlife snapshot owns the finite visit and
the one empty basket's home/hand/pen location. Restore validates both records
and restores garden work before the loan. Normal garden conversation stays
available during the visit and pauses the borrowed actor with the animals.
Neither a second worker nor a town actor is created.

Explicit saves retain animal positions, modes, animation clocks and bird return
cooldowns, plus worker feet, visit step and contact time. Only visit milestones
enter `progress_dict`, so ordinary grazing, flight or walking does not trigger
disk autosaves. Pickup, placement and pat contacts checkpoint once. A blocked
gather waits for both sheep to arrive before the affectionate beat; Caelan
remains free to move. Contact checkpoints do not replay after Continue.

Birds scatter within 50 pixels, then wait at least eight active seconds and
until Caelan is over 80 pixels from the landing. Sheep/bird/wing cues are finite
and share one low-priority wildlife family. Their near/far distances are
24/140 pixels, with source cooldowns of four seconds (eight for wings). Existing
regional allocation and lifecycle code owns all channels. Cat and butterflies
are silent. The art and review remain implementation review, without a claim
of user approval.

## Geometry reference

Coordinates below are global pixels, with 24 pixels per map tile. Routes were
sampled at intervals no greater than one pixel through production
`OverworldWorld.can_stand`, including existing scenery and work-controller
blockers. The initial checks used main's geometry before wildlife was added;
dynamic wildlife, its basket and Caelan still require collision checks at runtime.

The southern pen spans x `[-504,-240]`, y `[1392,1632]`; the eastern pen spans
x `[1308,1596]`, y `[1320,1524]`. Their north gates center on x `-360` and `1440`.
Sheep never pass those gates. These short grazing triangles pass with `(16,8)`
foot probes, 37 samples each; each returns to its first point:

| Existing animal ID | Grazing points |
| --- | --- |
| `south_sheep_a` | `(-420,1476) → (-428,1482) → (-416,1486)` |
| `south_sheep_b` | `(-314.4,1572) → (-322.4,1578) → (-310.4,1582)` |
| `east_sheep_a` | `(1368,1392) → (1360,1398) → (1372,1402)` |
| `east_sheep_b` | `(1526.4,1464) → (1518.4,1470) → (1530.4,1474)` |

The gardener's post-care home is `(-552,1164)`. With a new empty basket at
`(-516,1226)` and an `(18,4)` footprint, pickup feet must be `(-532,1226)`:
`home → (-532,1164) → (-532,1226)` passes 84 samples with the basket present.
After pickup, the clear outbound route is `(-532,1226) → (-480,1226) →
(-420,1226) → (-360,1226) → (-360,1408) → (-384,1424)`; reverse it before
replacing the basket and returning home. The original complete court/gate route
passed 472 samples with a `(10,6)` worker probe. The garden's east hedge at
x `-492` extends to y `1199.6`, so crossing east at y `1226` is essential.

At the pen, the basket stands at `(-360,1424)` and worker at `(-384,1424)`.
The approaches from each sheep's initial position are A `→ (-420,1452) →
(-404,1436) → (-384,1440) → (-381,1433)` and B `→ (-300,1512) → (-324,1464)
→ (-348,1440) → (-347,1430)`. The initial approaches passed 71 and 153 samples;
the final contact adjustments passed another nine and twelve samples against
the worker and solid basket. Sheep A's feet leave a two-pixel gap below the
worker while the hand reaches its fleece; B's muzzle reaches the basket without
overlapping its ground footprint. Return to the authored initial point along
the grazing triangle before joining a gather route.

The southern cat doorstep `(-420,1182)` is the existing farmhouse door approach.
Its connected route `→ (-420,1206) → (-450,1206) → (-450,1210)` passes 61 samples
with a `(10,5)` probe. An exhaustive pairwise comparison against all sampled
worker-route feet found no overlap. Keeping this route north of the gardener's
y `1226` lane prevents a head-on wait during the return. There is no old cat
record to remove.

The existing birds' landing points `(-840,228)` and `(-1128,-1603.2)` are clear
with `(6,3)` probes; small stationary spilled-grain patches can make their
feeding purpose visible without changing the farm's handled or reserve sacks.
Existing flowers are `south_flowers=(-446.4,1168.8)` and
`orchard_flowers=(-127.2,-264)`. The old butterfly positions are not flower
clusters: any additional landing target needs visible flowers. A straight
orchard approach crosses a harvest basket, and a straight southern approach
crosses the garden hedge; flight must account for elevation or take a clear arc.

The four sheep IDs above plus `west_bird`, `clearing_bird`,
`south_butterfly` and `orchard_butterfly` resolve to four sheep, two birds and two
butterflies in total. Remove their old draw counterparts at the static-prop
boundary, retaining all unrelated props and authored recipe identities. World
ownership must survive chunk eviction. The gardener's original `(position,
elapsed)` save fields remain owned by garden work during a loan; wildlife owns
the borrowed feet and restores only after garden restoration. Activation must
cover the whole home-to-pen corridor, beyond the garden's original 260-pixel
radius.

For gameplay capture, Caelan's `(24,12)` probe follows
`(-526,1214) → (-492,1214) → (-492,1250) → (-336,1250) → (-336,1412) →
(-280,1412)`. The eastward first leg passes above the home basket; x `-336`
clears the north gate and leaves the worker's x `-360` lane free. Watch from
the final point east of both sheep approaches: waiting at `(-336,1450)` blocks
sheep B. Escort in stages, then reverse the route during the worker's return,
so distance activation does not freeze the visit. The apparently nearby
x `-330` gate approach clips the fence.

## Validation and evidence

Run `python -m pytest tests -q` for the production suite; parallel verification
may add `-n 3` when pytest-xdist is installed. The art builder's independent
determinism check is `python tools/build_regional_wildlife.py --check`.
[Actual-game review](reviews/purposeful_wildlife/README.md) includes the full
2:58 video, individual clips, normal-scale frames, source hashes and measured
audio/Continue evidence. The PR records the full-suite result for its exact head.

Independent reviews checked route collision, actor/prop ownership, schema and
Continue, pause/travel, and actual contact frames. They exposed and resolved a
cat/worker lane deadlock and a Continue validation mismatch. Regression testing
also preserved garden repeat conversations and prevented birds from returning
while Caelan is still close to their away perch. Subjective audio listening is
not claimed; the review documents production-event PCM rendering and levels.
