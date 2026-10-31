# Garden and orchard work

Two region-owned actors bring the existing southern kitchen garden and village
orchard to life. They are separate from the sanctuary gardener and all town
household instances. The sites are about 1,500 pixels apart: a cross-site visit
would turn a small moment into a delivery, so the optional exchange is with
Caelan at the garden instead.

## Work and character

The kitchen gardener collects a wooden watering vessel beside a visible filled
rain barrel, dips it at the barrel, carries it along the open garden aisle,
waters two selected patches, returns the vessel, weeds and harvests two turnips
into the basket. After the finite batch she waits near a struggling potted
plant. E opens a short conversation; she accepts Caelan's suggestion of shade,
then lifts the plant, carries it beside the hedge and settles its leaves. The
scene ends with the plant in its new place. Full dialogue is read once per
journey; repeat interaction is brief. The plant does not magically recover.

The orchard picker approaches three accessible low branches through the existing
clear aisle. Each apple is picked, inspected, carried and sorted. Two usable
apples and one bruised apple occupy separate visible baskets. The final apple
gets a longer admiring pause. The picker then rests in the existing nook. Fruit
and turnips never respawn. Neither routine grants items, rewards or story flags.

## Implementation and persistence

`garden_orchard.py` owns two short authored action sequences. It does not add a
scheduler or delivery framework. Each portable object's position is derived
from completed pickup/placement actions and the current hand trajectory: one
vessel, one plant, two turnips, three apples. The seven objects remain controller
owned across streaming eviction.

The optional `overworld.garden_orchard` save record contains independent worker
phase, action index, action time, feet, greeting and read state. It is validated
without loading art. Older saves omit the field and start the work normally.
Continue restores the exact action and object ownership rather than rewinding a
carry to storage. Finishing the dialogue checkpoints its read state before the
plant move begins. Contact timestamps also checkpoint immediately, so Continue
after a contact cannot replay its sound. The autosave dirty signature excludes
per-frame feet and action time; those precise fields remain in explicit and
contact/step snapshots, without synchronous disk writes every animation frame.
Saving or streaming never creates a
second worker or crop.

Movement uses one-pixel foot-probe substeps through actual world collision.
Obstructions pause the worker; time does not advance through a blocked walk.
Workers occupy separate sites, avoiding narrow-lane reservation deadlocks.
The third orchard tree is approached via the west side of the existing bench.
All route/prop additions retain the existing garden entrance and orchard nook.
The world controller owns actors, draws their props with regional depth sorting,
and arbitrates interaction after existing bridge/farm interactions. Regional
travel continues to suspend the actors and virtual companions remain virtual.
Map, journal, pause, title and dialogue suspend work. Distant sites sleep.

## Sound

The merged regional audio controller receives finite `water`, `leaves` and
`basket` events at physical action beats, at the active worker's world position.
A placement emits at ground contact. Watering emits during the visible pour;
inspection/picking emits during leaf/fruit handling. There are no idle impacts.
The shared allocator retains its four-voice maximum, incidental family cap,
distance falloff and hard cutoff. No controller-owned mixer channels, queued
sounds, new sound engine, or audio dependency remains pending.

## Art and review

Dedicated carrying, can-carry, fill, water, weed, reach, sort, admire and rest
poses preserve approved layered body appearance and native scale. They are new
region-owned identities even though source appearance parts are reused. The
barrel, vessel, baskets, plant, apple and turnip use a retained generated source
sheet, mechanically cropped and registered for runtime; approved assets are
unchanged. See `assets/source/characters/garden_workers/README.md` and
`assets/characters/garden_workers/art.json` for provenance and contact offsets.
These assets have implementation review, not a claim of user art approval.

See [gameplay captures](reviews/garden_orchard/README.md) for actual-game video,
normal-scale stills, scripted fixture disclosure and the audible capture method.
Automated coverage is in `tests/test_garden_orchard.py`. No animal AI, interior,
bench interaction for Caelan, delivery, bridge/gate or quest changes are included.

## Validation boundary

The production regression command is `python -m pytest tests -q`. A broader
repository-wide pytest sweep also collects historical art tools. Three tests in
`tools/test_eldenmere_sanctuary_interior.py` fail unchanged on base main
`aa9456b5e75df711809c52eddbb6b190da036793`: optional inspection-line text,
old exported scene reconstruction, and old blocking-mask reconstruction. These
were reproduced in a detached baseline worktree (three failed, four passed).
This PR does not rewrite those unrelated sanctuary fixtures. The audio PCM
uniqueness check now covers the declared sound collection rather than hardcoding
the former seven-sound count; all ten materials pass its level/distinctness checks.
