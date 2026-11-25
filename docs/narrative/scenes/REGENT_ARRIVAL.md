# Iselin's arrival after the mill

MQ02's new ending brings Caelan back from Halden's restored mill to help
Serene and Tomas in the dining room at Serene's home. After the cup placement
and final exchange at home are acknowledged, the quest and its ordinary
rewards settle before this cinematic introduces Regent Iselin. Caelan stays
at home while the audience sees events elsewhere. The cinematic
returns control to his same dining-room position. MQ03 becomes available,
and Serene's separate request to meet the visitors accepts it.

## Scene and continuity

The arrival uses the same detailed pixel-art presentation as the opening and
battle scenes, with separately authored scenery, actor poses and animation.
The visual clock belongs to the cinematic rather than the exploration world.

1. The completed household cup-setting scene gets a short closing hold and a fade. The mill report no longer starts this cinematic.
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
   Iselin, her ledger-carrying page and the wagon continue walking throughout
   the ground-camera push. Separate foreshortened aerial artwork keeps the
   page present before the descent; he does not appear only after the stop.
   Guards wait closer to the gate, clear of the approaching party.
3. A modest relief caravan reaches the intact southern land checkpoint. A
   guard recognizes Iselin; their exchange establishes the longer ridge-road
   approach. The guards admit this expected party and remain on duty.
   Iselin, the page and the caravan turn into the gateway and recede along the
   painted road. A settled camera, shared road perspective and masonry occlusion make
   their passage into the valley visible. The wagon clears the gate before
   the scene fades out.
4. After the gate passage's short black transition, the party stops at the
   actual three-way junction at regional tile `(7,4)`. Stone leads north/slightly
   east to Eldenmere and west-southwest toward the ruined crossing; Iselin's
   rutted dirt approach joins from the south-southeast. The Carrier asks about
   deliveries and repairs while the page waits beside Iselin.
   After the player acknowledges "Were you here when it happened?", a 0.8-second
   camera traverse follows 122.068 tiles of the canonical main road west to the
   destroyed bridge. Directional blur and sparse tapered streaks affect scenery
   only and clear before the Carrier's two off-screen account paragraphs.
   The account remains player-paced. A clean cut returns to the exact crossroads
   camera and actor stations for Iselin's response about other incidents and
   the page's delivery notes. Nobody is transported to the bridge. River
   ambience belongs to the bridge insert, not the junction.
5. The caravan continues toward Eldenmere. Serene watches its approach from
   inside her home. Her private concerns acknowledge Iselin's difficult
   journey and their coming discussion. Tomas's cups return her attention to
   hospitality.
6. The caravan's arrival leads into its registered waiting location in town.
   The scene fades back to Caelan's actual MQ02 completion location.

The southern land gate and the broken western bridge are separate routes. The
caravan never crosses the ruined bridge. Neither its admission nor MQ02's mill
repair opens the player's regional checkpoints or repairs the crossing.

The lightning has an unknown cause. Only a handful of incidents have occurred.
This scene does not link the tusker's fallen tree to the strike, establish
Veinhold interference, disclose Serene's inherited warning, or authorize excavation.
The full covenant disagreement belongs to MQ03's later meal and discussion.
Iselin's expected visit was arranged beforehand; she did not set out because
Caelan restored the mill.

## Native acting foundation

The [sprite and animation standard](../../SPRITE_ANIMATION_STANDARD.md) owns Iselin's
appearance, body registration and complete-frame construction. Her current
arrival assets include static standing/listening/gesture/turn poses and the
left, rear-three-quarter and rear walks. Optional finite clips support one-time
performances. The first live clip is the gate stop and settle described below;
greeting, listening, speaking and turning remain separate performance changes.
The [foundation review](../../reviews/iselin_cinematic_foundation/README.md) records the
original playback mechanics and reference board at that milestone.

An arrival actor's `animation.json` can declare an `actions` object alongside
its existing `poses` and `loops`. Each named action has this shape:

```json
{
  "entry": [{"pose": "stand_left", "duration_ms": 120}],
  "hold": {"pose": "listen_left", "duration_ms": null},
  "recovery": [{"pose": "stand_left", "duration_ms": 140}],
  "rest_pose": "stand_left"
}
```

This example reuses existing stills to explain playback; it does not supply
drawn intermediate motion. Entry and recovery are nonempty lists of frames with
positive finite millisecond durations. The single hold frame uses a positive
finite duration or `null` for an indefinite, explicitly released hold. Frames
reference either a known static `pose` or a `file` within that actor manifest's
directory, with the same canvas dimensions. `rest_pose` names a static pose.
Drawn action frames retain the actor's common anchor, scale and depth contract.

The scene API is `play_actor_action(actor_id, action_name, cue_id)`,
`release_actor_action(actor_id, cue_id=None)`, `actor_action_state(actor_id)` and
`clear_actor_actions()`. Cue IDs identify authored events, not text pages or draw
calls. Duplicate IDs do not replay, including after the action settles; a new
cue during an unfinished action is rejected rather than queued. A release during
entry allows entry to finish before recovery. A settled action holds its rest
pose until another action or lifecycle clear returns presentation ownership.
Future performance PRs can wire the local dialogue cues they actually need.

Only unpaused, focused scene updates advance clip clocks. Drawing is read-only.
Phase changes, scene start/reset/restore, finish/Skip and Gallery close discard
the temporary players and cue history. Existing static and walking selection
continues when no action is active. The durable arrival receipt remains the
same version-one `waiting`/`pending`/`seen` record; action frames and clocks are
never serialized or used as quest completion signals.

### Gate stop and standing settle

Iselin approaches the gate at the existing 24 cinematic pixels per second.
At 1.25 seconds she has traveled 30 pixels and reaches the sixteenth approved
gate-walk drawing. The `stop_left` clip begins on that exact image, decelerates
with her final step, and settles into the approved `gate_stand_left` pose.
The gate uses the detailed `gate_walk_left` bank. During aerial descent,
`gate_incoming_left` cycles its first eight approved drawings without the later
stop anticipation. Its 16-pixel stride preserves the same two-pixel pose spacing
and joins the ground approach on the identical first frame. Longer travel shots
retain their existing generic `walk_left` cycle.

| Approach time | Movement and performance |
| --- | --- |
| 0–1.25 s | Original straight approach, root `[611,375]` to `[581,375]`, unchanged gait phase. |
| 1.25–1.75 s | Linear reduction of speed from 24 to zero, covering the final six pixels to `[575,375]`. Leading boot remains supported as the trailing boot closes. |
| 1.75–1.95 s | Root stays still; arms, coat and braid finish settling. |
| Greeting | Temporary stop ownership clears; the detailed gate standing pose remains, including the initial admission wait. |

The 700 ms clip uses the approved walk handoff for 40 ms, eight complete new
drawings at 60 ms each, a 60 ms hold, and 120 ms recovery on the approved idle.
The approved detailed drawings are sampled directly onto the 80×96 cinematic
grid with anchor `[40,92]`. Each source master has fixed whole-body registration;
neither feet nor changing occupied bounds determine per-frame scale. Complete
sources, high-resolution head/neck preservation, registration and immutable
approval hashes live under `assets/source/characters/iselin/cinematic_gate_left/`.
The earlier native stop source and its review remain historical evidence.

The approach camera retains its original 1.5-second pan and then holds.
Caravan, Lucan and page tracks still stop at 1.5 seconds; wagon/hoof audio follows
the caravan. Endpoints, dialogue and the subsequent gate passage are retained.
Only this left-facing gate stop is activated; other approaches keep their existing
performances until their gait phases and staging are reviewed.

A straight-moving actor can declare this bounded annotation:

```json
"stop": {
  "start_seconds": 1.25,
  "deceleration_seconds": 0.5,
  "settle_seconds": 0.2,
  "action": "stop_left"
}
```

`move_seconds` includes deceleration and must end at `start_seconds` plus
`deceleration_seconds`; the shot must leave room for the complete settle.
The finite action duration must equal deceleration plus settle. Scene updates
start the cue once and account for only the time since its boundary, including
when a large update crosses it. Drawing and reading dialogue do not trigger the
clip. Aerial ground-reference sampling uses the separate uninterrupted incoming
cycle and never borrows the live stopping action.

The [live detailed gate review](../../reviews/iselin_detailed_gate_live/README.md)
records production-loaded normal/slow captures, approved-pixel checks and
lifecycle validation. Initial review stationing selects the shot; production
updates then own all movement, action and camera selection. The earlier
[native stop review](../../reviews/iselin_walk_stop/README.md) remains historical.

## Controls and presentation

Dialogue advances at the player's pace and uses the shared in-game portrait
frame, speaker names, text scaling and pagination. Brief emotional cues remain
wrapped in literal asterisks. Serene's private thoughts are identified as such;
they are not dialogue that Caelan overhears.

Escape pauses and resumes the scene. A compact Skip button offers an immediate
handoff without granting another reward or accepting MQ03. Focus loss suspends
playback. Reduced Motion uses static framing and replaces the road whip-pan
with a direct bridge cut, without blur or moving streaks. Dialogue advancement
is disabled during the short traverse; its input cannot consume an unread
bridge paragraph. UI, portraits and controls draw after the native effect pass
and remain sharp. World movement, ordinary
interaction, quest staging, time and the exploration HUD remain suspended while
the cinematic owns the screen. Inputs that finish or skip it cannot continue
into exploration in the same event batch.

The Eldenmere theme fades with the home's closing view during the opening blackout.
**Royalty of the Realm** begins as the aerial arrival starts and plays for the
cinematic's duration. The later-journey opening leitmotif and battle music keep
their existing uses. Cinematic effects
respect the game's effects volume and release their channels when playback ends.
Recorded hawk calls and quieter, animation-timed wingbeats accompany the visible
bird. Hoofbeats and wagon sounds follow the party's movement and gait rate;
they stop when the party stops. Pause, focus loss, Skip and leaving the Gallery
also pause or release the appropriate voices. The recordings and source licenses
are documented in [the aerial sound assets](../../../assets/audio/sfx/regent_aerial/README.md).

## Durable handoff

`regent_arrival.py` owns a version-one record with `waiting`, `pending` and
`seen` states. It is included in the journey snapshot and progress signature.
Transient dialogue pages, camera positions and animation clocks are not saved.

- A fresh journey waits until the real MQ02 homecoming callback requests arrival; Halden’s mill report alone cannot start it.
- The acknowledged homecoming conclusion saves `pending` with the committed quest result and cup placement.
- Completing or skipping the cinematic saves `seen` and releases the visitors
  to their town staging. It does not accept or complete MQ03.
- Continuing a journey interrupted during arrival restarts the pending scene
  from its safe beginning. It does not repeat the homecoming ending, mill report or quest rewards.
- Older journeys with completed MQ02 and no arrival record migrate to `seen`.
  They retain their existing quest stages without an out-of-sequence cinematic.
- New Game resets arrival alongside the other story controllers.

The quest controller uses this handoff to hide new caravan staging while the
arrival is pending. Afterward, the same party waits at the corrected approach;
accepting the visit does not create a second Iselin or wagon.


The arrival capture verifies MQ03's introductory request, greeting and welcome
meal, stopping at `hosted` with MQ03 active and MQ04 locked. The later survivor
report, secret deployment, Mira rejoin and Sanctuary journey are covered by the
[current emergency review](../../reviews/mq03_emergency/README.md). The earlier
revised-visit review remains historical; its old CLI entry now delegates to the
current emergency driver without overwriting that archive.

## Assets and review

`assets/story/regent_arrival/scene.json` contains the playable dialogue and
choreography. Scenery and actor exports live alongside it, with original image
generations and provenance under `assets/source/cinematics/regent_arrival/`.

The exporters register authored artwork; they do not redraw the existing
world, character sprites or portraits. Existing gameplay routes and regional
barriers remain authoritative for the cinematic's geography.

The new crossroads background is offline composition of retained raw scenery
materials, not a new image generation or an enlarged regional-map crop. Its
4928×1728 panorama uses one invertible 28×24px-per-tile ground-plane projection.
Camera samples follow the road's actual arc distance, without invented shortcuts
or substituting the intact town bridge. It loads once, decoding to 34,062,336
bytes. The new bridge illustration assembles retained outer masonry columns
while preserving the canonical river, deck depth, physical span and open collapse.
Original region data, existing scenery PNGs and all existing character PNGs
remain unchanged. Clerk locomotion is independently offline part-authored; its
side, quarter and rear loops keep the same ledger hand and fixed limb lengths.

```sh
python tools/build_regent_arrival_scenery.py --check
python tools/build_regent_iselin.py --check
python tools/build_regent_clerk_walk.py --check
python tools/build_regent_arrival_actors.py --check
python tools/build_regent_aerial_actors.py --check
python tools/build_regent_crossroads.py --check
PYTHONPATH=tests python -m unittest test_regent_clerk_walk test_regent_crossroads_art test_regent_road_pan test_regent_crossroads_gameplay test_iselin_replacement test_regent_arrival test_regent_arrival_staging test_regent_quest
python tools/capture_regent_arrival.py
python tools/capture_regent_arrival_polish.py
python tools/capture_regent_crossroads.py
python tools/capture_regent_crossroads.py --check
```

The current [clerk and crossroads review](../../reviews/regent_crossroads/README.md)
contains the uninterrupted arrival, a focused crossroads/bridge clip, native
pose/contact sheets, geographic overlays and reproducible validation receipts.

The [gate and transition review](../../reviews/regent_arrival_polish/README.md)
records earlier staging. The predecessor's
[historical side-walk review](../../reviews/aldric_side_walk/README.md) is archived
implementation evidence. Current Iselin scenes use complete authored poses,
her approved 16-frame walks, and a new rear-three-quarter cycle, exported by
`tools/build_regent_iselin.py`. The current native integration review records the
cinematic, meal, Sanctuary and save-checkpoint checks.
The full arrival can also be replayed from the title screen's **Gallery** as
**Iselin's Relief Caravan**, without loading or changing a journey.

The [aerial-opening review](../../reviews/regent_aerial/README.md) records the
bird-led introduction and its continuous handoff to the gate. Its geographic
reference comes from `assets/maps/overworld/elden_vale/region.json`; cinematic
art and animation sources are retained under
`assets/source/cinematics/regent_aerial/`.

The [road approach and audio review](../../reviews/regent_caravan_revision/README.md)
includes an uninterrupted preview with the actual runtime sound mix, road-contact
measurements, walking and guard-clearance evidence, and a bird-sound audition.

See the [production-game review](../../reviews/regent_arrival/README.md),
[MQ03 guide](../../REGENT_QUEST.md), [regional surge context](../game_01/REGIONAL_SURGES.md)
and [covenant](../world/SANCTUARY_COVENANT.md).
