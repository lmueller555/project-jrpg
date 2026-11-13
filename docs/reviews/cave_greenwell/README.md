# Greenwell Chamber

The continuous cave gains a green-crystal chamber between Deep Gallery and the
final Quiet Shelf/Echo Chamber approach. The authored main route crosses it;
the old shelf approach remains traversable for checkpoint compatibility.
The room and pool bank are safe from random encounters. The existing water kit
supplies the pool and solid water mask; green microcrystals use the final slot
in the existing 32-source light budget. No new scene/save identifier is needed.

At the reachable southwest bank, E faces Caelan toward the spring and invokes
magical rest: every active party member recovers full effective HP and MP,
including KO recovery. It opens feedback dialogue and checkpoints the ordinary
party resource state. Rest is reusable, consumes no inventory, grants no quest
progress, and respects the cave controller's modal and line-of-sight guards.
There is no water pickup or carried prop.

After the durable Vespermaw defeated flag becomes true, actual swept travel
consumes encounter distance at 0.5 credit. Both spending and exact trigger
interpolation use the same factor. Pending tickets, random seeds, formations,
levels, safe-area protection and save schema retain their existing behavior.
This approximately halves encounters per distance, rather than guaranteeing
half as many battles on each particular exit walk.

Validation: 40 focused tests passed across Greenwell, encounter ownership,
cave topology, controller, boss state and chasm suites. Deterministic cave
builder --check passed. Comparing full collision rasters to main found zero
previously walkable pixels newly blocked. chamber.png is an isolated production
cave-renderer frame at camera (1630,530), Caelan (2000,828), 1000 ms; no saves.
The view was inspected for readable bank access, crystal lighting and water.

Broader gameplay checks have existing baseline failures: cave random gameplay
and boss gameplay setup stall in the Sanctuary entrance approach at (444,642),
while cave gameplay's real-walking test expects the battle music but receives
something_is_wrong. All reproduce in a detached, unchanged main checkout at
5b7d4587. Two other cave gameplay cases pass. These unrelated failures were
left unchanged; the broader suites are not claimed green.
