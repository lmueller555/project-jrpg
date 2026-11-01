# Aldric's arrival after the mill

The fully acknowledged MQ02 report commits the repaired mill and its ordinary
quest rewards before a cinematic introduces Regent Aldric. Caelan stays at the
mill; the audience sees events elsewhere. MQ03 becomes available, and the
player still accepts it through Serene's preparations dialogue inside the
sanctuary dining room.

## Scene and continuity

The arrival uses the same detailed pixel-art presentation as the opening and
battle scenes, with separately authored scenery, actor poses and animation.
The visual clock belongs to the cinematic rather than the exploration world.

1. The completed mill gets a short closing hold and a fade.
2. A bird leads an aerial view west across the actual Elden Vale landscape,
   then banks left toward the south. The view establishes the two boundary
   rivers, northern woodland, eastern foothills, village, farms and damaged
   western crossing. Following the bird over the southern wall reveals the
   guards and approaching relief caravan from above. The camera descends and
   passes beneath the nearby canopy before easing into the gate scene. This
   foreground pass conceals the registered transfer between aerial and ground
   views; the scenery never dissolves between the two perspectives.
   The caravan follows the painted approach road before the canopy pass. The
   descent leaves three additional seconds to watch the approach, and both
   Aldric and the wagon continue walking throughout the ground-camera push.
   Guards wait closer to the gate, clear of the approaching party.
3. A modest relief caravan reaches the intact southern land checkpoint. A
   guard recognizes Aldric; their exchange establishes the longer ridge-road
   approach. The guards admit this expected party and remain on duty.
   Aldric and the caravan turn into the gateway and recede along the painted
   road. A settled camera, shared road perspective and masonry occlusion make
   their passage into the valley visible. The wagon clears the gate before
   the scene fades out.
4. Inside the wall, Aldric listens to local accounts of the lightning strike
   and its consequences for ordinary deliveries. The ruined western crossing
   provides a physical view of the damage. His questions, practical response
   and reluctance to promise an unsupported date establish his responsibilities
   and fatigue.
   A brief black transition separates the gate passage from this later stop.
   The riverbank fades into view and holds on the ruined crossing before the
   conversation begins; travel effects give way to river ambience.
5. The caravan continues toward Eldenmere. Serene watches its approach from
   inside the sanctuary. Her private concerns acknowledge Aldric's difficult
   journey and their coming discussion. Tomas's cups return her attention to
   hospitality.
6. The caravan's arrival leads into its registered waiting location in town.
   The scene fades back to Caelan's actual MQ02 completion location.

The southern land gate and the broken western bridge are separate routes. The
caravan never crosses the ruined bridge. Neither its admission nor MQ02's mill
repair opens the player's regional checkpoints or repairs the crossing.

The lightning has an unknown cause. Only a handful of incidents have occurred.
This scene does not link the tusker's fallen tree to the strike, reveal an
ancient mechanism, disclose Serene's inherited warning, or authorize excavation.
The full covenant disagreement belongs to MQ03's later meal and discussion.
Aldric's expected visit was arranged beforehand; he did not set out because
Caelan restored the mill.

## Controls and presentation

Dialogue advances at the player's pace and uses the shared in-game portrait
frame, speaker names, text scaling and pagination. Brief emotional cues remain
wrapped in literal asterisks. Serene's private thoughts are identified as such;
they are not dialogue that Caelan overhears.

Escape pauses and resumes the scene. A compact Skip button offers an immediate
handoff without granting another reward or accepting MQ03. Focus loss suspends
playback. Reduced Motion uses static camera framing. World movement, ordinary
interaction, quest staging, time and the exploration HUD remain suspended while
the cinematic owns the screen. Inputs that finish or skip it cannot continue
into exploration in the same event batch.

The Eldenmere theme accompanies this present-day scene. The later-journey
opening leitmotif and battle music keep their existing uses. Cinematic effects
respect the game's effects volume and release their channels when playback ends.
Recorded hawk calls and quieter, animation-timed wingbeats accompany the visible
bird. Hoofbeats and wagon sounds follow the party's movement and gait rate;
they stop when the party stops. Pause, focus loss, Skip and leaving the Gallery
also pause or release the appropriate voices. The recordings and source licenses
are documented in [the aerial sound assets](../assets/audio/sfx/regent_aerial/README.md).

## Durable handoff

`regent_arrival.py` owns a version-one record with `waiting`, `pending` and
`seen` states. It is included in the journey snapshot and progress signature.
Transient dialogue pages, camera positions and animation clocks are not saved.

- A fresh journey waits until the real MQ02 report callback requests arrival.
- The mill conclusion saves `pending` with the committed quest result.
- Completing or skipping the cinematic saves `seen` and releases the visitors
  to their town staging. It does not accept or complete MQ03.
- Continuing a journey interrupted during arrival restarts the pending scene
  from its safe beginning. It does not repeat the mill turn-in or its rewards.
- Older journeys with completed MQ02 and no arrival record migrate to `seen`.
  They retain their existing quest stages without an out-of-sequence cinematic.
- New Game resets arrival alongside the other story controllers.

The quest controller uses this handoff to hide new caravan staging while the
arrival is pending. Afterward, the same party waits at the corrected approach;
accepting the visit does not create a second Aldric or wagon.

## Assets and review

`assets/story/regent_arrival/scene.json` contains the playable dialogue and
choreography. Scenery and actor exports live alongside it, with original image
generations and provenance under `assets/source/cinematics/regent_arrival/`.

The exporters register authored artwork; they do not redraw the existing
world, character sprites or portraits. Existing gameplay routes and regional
barriers remain authoritative for the cinematic's geography.

```sh
python tools/build_regent_arrival_scenery.py --check
python tools/build_regent_arrival_actors.py --check
PYTHONPATH=tests python -m unittest test_regent_arrival test_regent_arrival_staging test_regent_quest
python tools/capture_regent_arrival.py
python tools/capture_regent_arrival_polish.py
```

The [gate and transition review](reviews/regent_arrival_polish/README.md)
shows the corrected walk cycle and continuous gate-to-riverbank sequence.
The full arrival can also be replayed from the title screen's **Gallery** as
**Aldric's Relief Caravan**, without loading or changing a journey.

The [aerial-opening review](reviews/regent_aerial/README.md) records the
bird-led introduction and its continuous handoff to the gate. Its geographic
reference comes from `assets/maps/overworld/elden_vale/region.json`; cinematic
art and animation sources are retained under
`assets/source/cinematics/regent_aerial/`.

The [road approach and audio review](reviews/regent_caravan_revision/README.md)
includes an uninterrupted preview with the actual runtime sound mix, road-contact
measurements, walking and guard-clearance evidence, and a bird-sound audition.

See the [production-game review](reviews/regent_arrival/README.md),
[MQ03 guide](REGENT_QUEST.md), [regional surge context](narrative/game_01/REGIONAL_SURGES.md)
and [covenant](world/SANCTUARY_COVENANT.md).
