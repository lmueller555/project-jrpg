# Fire Veinhold prologue — cinematic production

**Status:** Shot 8, Bridge Ascent, is implemented in the Gallery. The eight-shot
film lasts **55 seconds**, with the new shot occupying 47–55 seconds at native
960×640 and 60 Hz. Frozen source exports, the complete 481-sample normal/Reduced
Motion bank, fresh reproduction and Gallery validation are recorded in the
[Bridge Ascent review](../../reviews/veinhold_bridge_ascent/README.md).
The playable infiltration handoff remains future implementation.

[Chapter 1](../game_01/CHAPTER_01.md) owns the opening story. This document owns
cinematography and implementation. The [sprite standard](../../SPRITE_ANIMATION_STANDARD.md)
owns artwork construction. The [Cinder Isles guide](../world/POLAR_REGIONS.md#cinder-isles)
owns the approved geography; the canonical world map remains unchanged.

## Shot order

| Shot | Reel time | Picture and disclosure |
| --- | --- | --- |
| 1 — Eagle Ascent and Cinder Isles | 0–25s | Follow the eagle east-southeast over Merovar's coastal summit for 15 seconds, then hold the offshore volcanic vista for ten seconds. The bird leaves below frame by 17s. Amber facility operation is visible; red alarms have not activated. |
| 2 — Island Orbit | 25–30s | A continuous five-second, 180° orbit around the main isle ends looking back toward Merovar. All 301 camera samples are rendered perspectives from one shared spatial scene. |
| 3 — Fortress Alarm | 30–34s | Hold the reverse angle for four seconds while red warning lights blink and the industrial siren sounds. The audience has two full warning cycles before the rush. |
| 4 — Bridge Rush | 34–35s | Fly past the facility and along the Merovar bridge in one second, with directional motion cues and changing sound perspective. |
| 5 — Frozen Bridge | 35–39s | Settle 20 feet onto the bridge from its Merovar mainland landing, facing mainland. Distinct Carcovian guards are frozen in stasis; ice coats parts of the deck and railings. The attackers remain unseen behind the camera. |
| 6 — Running legs | 39–42s | Cut to boot-height side tracking of Iselin, Lucan and the Crown soldier running toward the Veinhold over the steel bridge. Their faces stay outside the frame. |
| 7 — Faces | 42–47s | Track backward in front of the runners, starting above their heads and tilting down over 1.5 seconds to reveal their faces. Lucan leads in the center. Iselin is on his anatomical right, close behind (screen left); the Crown soldier is on his anatomical left (screen right), about ten feet behind. |
| 8 — Bridge Ascent | 47–55 seconds | Continue from Shot 7's exact terminal camera and running phase, rise above Lucan, then widen to a high view of the bridge with mainland up and fortress down. Four frozen guards remain behind the party; six guards advance from the fortress and two more emerge through its visible gate late in the shot. |

The fortress access bridge is distinct from Elden Vale's western bridge. The
five-second orbit replaces the previously proposed separate 15-second closer
fortress shot. There is no cast reveal or new dialogue in Shots 2–5. Shot 6
reveals their lower-body movement before Shot 7's frontal face reveal; Shot 8
continues that performance into the high bridge view.

## Shot 1 staging

The eagle starts high on the final approach, closer to the summit than the
previous valley composition. Its authored forward speed begins at 28 scene
units/second (previously 18), and its initial height is 145 (previously 110).
These are staging units, not canonical geographic distances.

- **0–2s:** Powered flight over close moonlit rock.
- **2–5s:** A shallow bank and recovery toward the saddle.
- **5–13.25s:** Powered climb with complete authored wing strokes.
- **13.25–15s:** Glide across the crest; the camera clears the near ridge.
- **15–25s:** A full ten-second view of the Cinder Isles. A restrained camera
  push continues while the eagle descends below the camera and leaves the frame.

A single tall opaque painting contains the summit approach, coastal descent,
open sea and islands. The camera's source window pans upward from the rocky
approach into the upper vista. Every geographic landmark shares one transform;
there are no independently scrolling foreground/background mountain groups,
terrain-card seams, panorama cross-fades or hard cut at the crest. At 15s the
upper vista is fully framed; the nearer mainland ridge has passed below the
main view. The camera releases its eagle chase at the crest. The eagle descends smoothly
through the lower edge at full sprite scale, clearing the frame by 17s. The
camera keeps pushing toward the fortress through 25s; the remaining vista is
unobstructed. The bird neither fades nor shrinks away.

Nighttime remains readable: cool silver rock and eagle lighting, a dark starry
sky, moonlight on the sea, rust-red main-island ash, and lava on the distant island. This is
not a sunrise, tropical archipelago or view of Adamanthra's Ice Dome.

## Geographic composition

The camera faces **east-southeast** from the mountains southeast of Eldenmere.
Eldenmere lies behind the camera. Merovar's rocky coast gives way to a broad
sea channel, followed by the main Cinder volcanic island. The smaller active
island lies farther beyond its right shoulder; southern rocky skerries appear
to the right. Othara's distant rust-colored headlands occupy the left horizon.
Istrava lies south of the archipelago and outside this framing.

The main island is substantially wider, with broad flat coastal terraces for
the fortress, reservoir and military infrastructure. Its volcano is
inactive because the Veinhold is extracting Fire-aspected aether: no glowing
crater, lava flows or eruptive fire remain. It still releases light steam/gas.
The distant volcano retains its active glow and a denser ash plume. Othara's
Damar Drylands remain a separate landmass.

Two large steel bridges are visible. The nearer bridge runs from Merovar's
rocky mainland coast to the main island's front terrace. The farther bridge
runs from the Damar headlands on the left to the island's rear-west approach.
Both have complete abutments, steel decks and piers scaled to perspective.
The final source window begins at y50. The lens widens slightly at the crest
to retain the expanded fortress and nearer Merovar landing, then makes a
restrained push during the vista. The approved
Fire Veinhold site is on the main island near the volcano; the fortress and
reservoir are visible in this wide shot and remain in the shared orbit layout.
Exact geographic distances, travel times, political control of the crossings
and the infiltration mission's detailed route remain open. The cinematic's
staging dimensions do not establish a geographic survey.
The world map is illustrative and supplies relationships rather than a precise
bearing grid or guaranteed real-world line of sight.

## Art and runtime contract

The production shot list is `assets/story/fire_veinhold_opening/scene.json`.
Its eight shots total 55 seconds.
Shot 1 explicitly records `ascent_duration:15`, `vista_duration:10`, and
`duration:25`. Durations must be positive, finite and sum correctly.

The native picture remains **960×640**, full **3:2**, rendered directly to the
actual UI surface. The new perspective sequences are authored at **60 FPS**;
frame selection follows elapsed scene time, so a slow render drops samples
without lengthening a shot. The new opaque panorama is **1024×1536**, with vertical
overscan for the climb. Its source, references, prompt, hash and export framing
are retained under `assets/source/cinematics/fire_veinhold/shot01/environment/`.
`tools/build_prologue_mountains.py --check` verifies reproduction.

The eagle retains its complete 256×256 drawings, density two, chest anchor
[128,144], and 750ms powered-wing cycle. Animation follows real elapsed time:
extending the shot does not slow its wing cadence. The bank spans three seconds.
The second powered window ends at 13.25s on the shared neutral wing pose.
The eagle retains its whole-body scale as it descends out of frame; changing
wing bounds never drive registration or body proportions. Reduced Motion lowers
lateral sway while retaining the same phase durations, wings and geographic
reveal. Focus/pause freeze the entire presentation.

Wind continues across the crest and through the ten-second vista. The crest
rush is cued at 14.65s; feather Foley follows actual powered downstrokes only.
Audio leases respect effects volume, mute, focus and cleanup without stealing
music channels. The audio source folder retains its deterministic export recipe
and CC0 Foley attribution. Preview movies reconstruct audio from those exports
and cue metadata, rather than claiming hardware-loopback listening review.

## Veinhold architecture and operation

The fortress occupies the front-right terrace while the cold crater remains
above it. Its major readable shapes are the braced extraction works, command
keep and fortified circular reservoir. Two heavy conduits descend from the
lower-flank extraction structure into the basin. Captured aether glows amber
inside the channels and reservoir; it does not turn the dormant crater into
an erupting volcano. Walls, barracks and loading/service yards support the
main silhouettes. Both bridge gatehouses lead into visible compound roads.
Materials are charcoal basalt, blackened steel and weathered bronze. Banners
use charcoal cloth and a restrained copper split-ring/vertical-bar mark.

`cinematic_facility.py` draws restrained power packets down the authored
conduit paths toward the reservoir, floating ember accents within its interior,
with the red warning fixtures inactive until the 30-second alert cue. All
landmarks share the terrain projection. Windows and architecture remain
steady. The continuation uses camera-specific emissive layers with occlusion;
red alarms remain distinct from steady windows and amber power. Reduced Motion
uses steady red warning illumination and static amber accents.
Effects follow the scene clock, including pause/focus/restart; they introduce
no new dialogue, weapon identity or quest state.

### Faction identity and costume continuity

Carcovian soldiers use matte gunmetal segmented armor, charcoal cloth,
restrained copper accents and enclosed helmets. The Veinhold's charcoal banners
carry the same copper split-ring/vertical-bar visual mark. These shapes and
materials must remain distinguishable under moonlight and the blue cast of ice.
Red remains the warning-light color; it is separate from faction cloth.

Lucan retains his approved polished steel armor, oxblood cloth and gold edging.
His existing shield chevron is retained without assigning it a new heraldic
meaning. The accompanying Crown soldier has simpler companion-side equipment;
the new running artwork must preserve that distinction at boot and greave level.
Iselin retains her blue/silver royal clothing and directional costume identity.
The new cinematic appearances do not replace their ordinary world sprites.

## Complete drawn volcanic plume cycles

The repeated-puff effect and `smoke_puff.png` are removed from runtime. Both
vents now use sixteen complete authored plume drawings, registered by explicit
mouth landmarks to a fixed [70,230] anchor on 256×256 transparent canvases.
The four-second loop changes connected billows and dissolving wisps while the
vent stays on the crater mouth. Frame exports preserve transparent margins;
no cloud crosses a source cell boundary or reaches the exported canvas edge.
The rejected draft atlas remains only as the refinement source, not runtime art.

`cinematic_smoke.py` selects adjacent drawings from elapsed shot time and
blends them in premultiplied alpha before compositing. This avoids exposed PNG
rectangles and the opacity dip of ordinary overlapping cross-fades. It never
emits, translates or despawns copies of a puff texture. Main-island steam is
lighter; the farther active vent is denser, with a different cycle phase and
scale. Source coordinates use the same projection as the terrain.

The loop is deterministic under seeks and restart, freezes with pause/focus,
and advances more slowly under Reduced Motion. Source images, exact prompts,
vent landmarks, alpha cleanup and export recipe are retained in the environment
source folder. Tests check transparent boundaries, loop/vent registration,
visible motion at both vents and correct premultiplied blending. Native frame
and close-up movie review remain necessary alongside those checks.

## Shared island scene, orbit and bridge camera

The continuation is rendered offline from one spatial scene with painted
surfaces; Pygame remains a 2D presentation. A limited nonplanar relief preserves
the approved opening composition over the orbit's first three degrees, then
the shared island geometry supplies the remaining views. These are rendered
camera poses, not cross-fades between independent perspective paintings.
Both bridges, the dormant cone, extraction structure,
reservoir, fortified compound and mainland terrain occupy consistent world
positions. Materials retain charcoal basalt, blackened steel, bronze, rust-red
ash and cool nighttime lighting. The distant active cone remains distinct from
the drained main crater. Moonlight stays fixed in world space as the camera
turns; architecture never mirrors or rearranges during the orbit.

The 180° path ends facing approximately west-northwest toward Merovar's coastal
mountains. Its elevation and route maintain readable geography without clipping
through the cone or compound. The last orbit pose is the alarm hold's first
pose. The rush follows the Merovar crossing, not the Damar bridge, and reaches
the final deck position without passing through structural members.

The final camera is 6.096 metres (20 feet) along the bridge from its Merovar
abutment, measured toward the isle, and looks back toward mainland. Three
Carcovian guards are clearly visible in distinct interrupted-action poses;
the source retains four staged guard planes. Ice covers selected
deck plates, seams and railings, with a trail continuing fortressward behind
the camera. They are held in stasis; no blood or newly established deaths are
implied. Iselin, Lucan and the Crown soldier remain absent from picture,
reflections, identifying shadows and dialogue until their later reveal.

The four frozen guards use complete RGBA image planes at separately calibrated
depths. They are rigid full-character drawings, not volumetric character models
or silhouettes stretched out of the deck's depth field. The empty bridge/deck
background occupies separate geometry, preserving clean body contours during
the camera's late approach. The smoke reuses the approved complete plume
drawings on vent-anchored, camera-facing surfaces with depth occlusion. This
preserves their registration and painted appearance without claiming a
volumetric fluid simulation or physically fixed wind direction.

`continuation/manifest.json` supplies the rendered perspectives and separate
alarm layers. The 301 orbit samples cover times `0/60` through `300/60`: exactly
300 intervals and five seconds. The terminal sample supplies the following
shot's pose rather than adding a 301st display interval. The one-second rush
similarly has 61 inclusive samples. Hold/reveal loops retain fixed cameras;
they do not duplicate hundreds of identical backgrounds.

`cinematic_perspective.py` validates the manifest and loads a bounded working
set of frames. Its 24 image slots reserve at most **56.25 MiB** for decoded
images plus in-flight loads, excluding temporary drawing/conversion buffers.
PNG decoding runs in background workers; display conversion stays on the main
thread. No complete 301-frame atlas is eagerly decoded. Scene state queries
calculate frame and timing state without disk access. The cache
is released when a replay ends or restarts. Normal playback uses every authored
perspective when rendering keeps pace; Reduced Motion lowers camera intensity,
removes heavy rush effects and retains the same timing and disclosures.

## Running-party tracking shot

At 39s the held frozen guards cut directly to a three-second, low side view of
the attackers running toward the Veinhold. The party moves screen left to right;
deck seams, rivets and rail supports pass behind them in the opposite direction.
The composition stays below their faces. This is a first glimpse of the group
in motion, preceding the frontal face reveal.

Lucan leads. Iselin follows close on his anatomical right, nearest this camera;
the Crown soldier remains on his anatomical left, 3.048 metres (ten feet)
behind. The framing can admit the trailing soldier near its edge rather than
compressing that gap. Depth ordering follows those lanes and foreground bridge
members, with no duplicate body or equipment overlays.

Each runner uses complete authored drawings with both near and far legs resolved
in the source pose. Contact, compression, push-off, flight and recovery must
progress through the cycle with a coherent loop seam. Foot contact metadata
drives the corresponding metal footfalls. Each side-view production cycle has
24 complete poses over 800 ms, holding each drawing for two 60 Hz display ticks.
Lucan starts at phase zero; Iselin is offset 0.166666… seconds and the Crown
soldier 0.3 seconds. These phase differences keep their steps from becoming a
synchronized march. Display FPS and authored drawing cadence are separate.
World travel is 4 m/s. The side view uses a calibrated 942.15 pixels per metre
to retain the stance-foot excursion of the existing drawings at their slower
playback rate. Its final camera drift is reframed to preserve the trailing
soldier's visibility. This calibration is staging evidence, not a claim of
perfect pixel-level foot locking throughout every authored pose. Simply
accelerating a walk, sliding a whole idle or rotating detached limbs cannot
supply this performance.
Cloth and armor movement follow the same authored phase.
The party's explicit side-shot starting marker is 22.26 metres, independent of
camera drift. Three seconds of travel reaches the frontal marker at 34.26 metres.

`shot06/scene.json` supplies the runner sources, registration, cycle phases,
formation and bridge framing to `cinematic_bridge_run.py`. The shot has its own
native 960×640 renderer and bounded character-image cache, separate from the
perspective sequence's 24 image slots. State queries sample elapsed time without
loading images. All temporary runner and background surfaces are released on
completion, restart and scene close. Review metadata reports the two caches
separately so the perspective budget is not mistaken for the whole presentation.

The lateral environment separates fixed far sky/sea/mountains from a complete
rail-and-deck painting with authored transparent gaps. Both retain the same
3:1 source registration and are uniformly exported to 1920×640 by
`tools/export_prologue_bridge_background.py`. The original combined painting
remains a design reference. Sources, prompts and exact export recipes stay under
the Shot 6 source directory. Alternating mirrored scenery tiles share their edge
pixels during tracking; character drawings and costume sides are never mirrored.

Normal and Reduced Motion versions preserve the same three seconds, character
cadence, party spacing and disclosure. The far scenery stays fixed in both
versions. Reduced Motion removes optional camera back-drift while retaining
the ground speed needed by the foot-contact cadence. Pause and focus loss
freeze character, scenery and audio clocks
together. No face close-up, overhead reveal, new dialogue or playable mission
handoff is included in this shot.

## Frontal face reveal

Shot 7 begins at 42s with the camera in front of the advancing party, tracking
backward toward the Veinhold. It starts above their heads and tilts down over
the first 1.5 seconds. The remaining 3.5 seconds give their faces time to read
while the run continues. The native shot lasts five seconds at 60 FPS: 300
display intervals. The environment's inclusive terminal camera sample supplies
the handoff pose rather than adding an extra displayed interval.

Lucan leads in the center. Iselin stays close behind on his anatomical right,
which appears on screen left in this frontal view. The ordinary Crown soldier
remains on Lucan's anatomical left, screen right, 3.048 metres behind. The
relative depth and apparent scale preserve that gap. This is local performance
staging farther toward the fortress; it does not relocate the party to the
frozen-guard camera or establish a geographic travel measurement.

The complete frontal drawings use the detailed painterly treatment of the
frozen guards, while retaining the companions' approved identities and costume
colors. Lucan keeps dark swept hair, polished steel, oxblood cloth and gold
trim. Iselin keeps white hair, blue eyes and blue/silver royal clothing. The
Crown soldier's simpler equipment remains distinct from Carcovian gunmetal,
charcoal and copper. Running effort belongs in coherent face, head, shoulder,
arm and cloth movement rather than independently bobbing a static portrait.

Each runner has 48 complete frontal poses over 800 ms. The side view's global
clock continues through the cut: at 42s Lucan begins at phase 0.6 seconds,
Iselin at 0.766666… and the Crown soldier at 0.1. These are the preceding
three seconds plus each side-view offset, modulo the shared 0.8-second cycle.
The continuous quantities are gait phase and contact timing; the side and front
frame indices differ because their drawing counts differ. Every displayed
60 Hz tick advances the authored frontal pose. Near/far or anatomical limb
identities, equipment occlusion and body proportions must remain coherent
through the full cycle.
The source drawings and the visible frontal performance receive their own
review; the preceding boot-height review does not establish frontal quality.

The frontal party starts at the explicit bridge-local marker 34.26 metres and
travels at 4 m/s. `starting_party_metres` is independent of speed, so retiming
the run does not relocate its opening camera or party position. The existing
camera height, lens, 1.5-second tilt and party formation remain intact.

`cinematic_face_reveal.py` supplies the same camera and complete-drawing
projection to the offline bake and runtime timing queries. The production
`shot07/scene.json` selects `baked_characters: true`: all three complete actors
are composited into the 301 native 960×640 camera samples before shipping.
There are 300 displayed intervals and one inclusive terminal sample. Runtime
streams those final pictures through eight image slots, reserving at most
18.75 MiB for decoded pictures plus pending loads, excluding temporary
drawing/conversion buffers. It retains no separate actor image bank. The
RGBA drawing exports (768×1024 for Lucan and the soldier; 1024×1024 for
Iselin's wider flowing silhouette) and their metadata remain reproducible authoring
inputs and timing references, rather than an eagerly decoded 144-pose runtime
cache. The scene's sample metadata still reports actor pose, phase and placement
for QA and contact synchronization.

Full-film and standalone frontal playback use the same streamed production
bank, warning, wind and footstep phases. Other individual clips do not load
that owner. Capture metadata records decoded/pending bytes and verifies that
completion, restart and close release the temporary owner. No dialogue,
overhead ascent or playable handoff is introduced here.

## Bridge Ascent — production contract

Shot 8 occupies **47–55 seconds** at native **960×640**, 60 Hz. Its 481 inclusive
camera samples run from local `0/60` through `480/60`: **480 displayed intervals**,
exactly eight seconds. The complete film therefore has **3300 displayed ticks**
over 55 seconds; inclusive terminal samples do not add display time.

The entry uses Shot 7's exact terminal camera pose, lens, party world positions
and gait phase. The current composite using all three actual cast sources
matches Shot 7's terminal sample 300 pixel for pixel. It rises continuously
above Lucan before opening into a high view of the crossing. Mainland stays at
the top and the fortress at the bottom;
screen right remains bridge-local −X through the overhead portion, without a
roll or basis flip. The current shared rig rises from 1.55 metres at entry to
4 metres at 0.8 seconds, 22 metres at 2.2 seconds and approximately 300 metres
at the end. Its optical axis reaches straight down at 2.2 seconds while the
camera subsequently reframes along the bridge. These are cinematic staging
coordinates, not new geographic distances or travel times.

The party continues toward the Veinhold at **4 m/s**, from bridge marker 54.26
to 86.26 metres. Lucan remains central; Iselin stays 0.65 metres on his anatomical
right and 0.5 metres behind, and the Crown soldier stays 0.75 metres on his
anatomical left and 3.048 metres behind. Their 800 ms run cycle continues across
the cut. Entry phases are **0, 1/6 and 0.3 seconds** for Lucan, Iselin and the
Crown soldier respectively; these are phases 0, 10 and 18 of the 48-pose cycle.
They are not three new synchronized starts. Contact Foley follows the same
continuous clock.

Four frozen Carcovian guards retain their established world positions and
distinct interrupted-action poses behind the party. They remain in stasis.
Six live Carcovian guards advance from the fortress side toward the party;
two further guards emerge from the gate late in the shot, after the gate has
entered the picture. Their direction, spacing and gate exits must be readable
in the actual projected frames. The steel deck, rails, ice trail, water and
both landings retain one spatial layout through the rise.

New elevated appearances require complete, detailed party and guard drawings
with camera-appropriate anatomy, equipment, hair, cloth and occlusion. Approved
Shot 7 art remains valid and reusable for the entry where its view applies.
Tilting or vertically squeezing frontal PNGs cannot supply the later elevated
views. Each actor's view follows the ray from that actor to the camera: a
straight-down optical axis does not make every off-axis actor a 90° top view.
Native review covers the exact entry, close transition, later cycle and
source-batch joins; see the [inspection record](../../reviews/veinhold_bridge_ascent/independent_review/final_bank_review.json).
Rough guides and phase metadata remain construction inputs. Acceptance is bound
to the frozen exported drawings and their actual native projection.

Each party export describes 133 logical transition rows through local 2.2
seconds, followed by a 48-phase elevated cycle. These are sample/timing records,
not a promise of 133 unique transition drawings. An authored pose can be exposed
for two 60 Hz ticks: the Crown soldier's odd transition rows hold the preceding
pose, and Iselin's phase-32 passing drawing covers rows 118–119. Lucan's rows
36–37, 40–41 and 44–45 expose the complete drawings authored at phases 37, 41
and 45 respectively. His logical phase and the 48 contact remain unchanged.
The scene clock, camera and contact phase still advance at each tick. Judge
these exposures and their joins in native projection rather than treating
unique-file count as a motion requirement.

All three party exports and the guard export are frozen for this revision and
rebuild from their retained sources. Each party retains 133 logical transition
records and 48 cycle records. The Crown soldier references 127 unique PNGs,
Iselin 168 and Lucan 156. The
[source freeze and export evidence](../../reviews/veinhold_bridge_ascent/source_checks/frozen_profiles.json) records
the final manifests, raw/export hashes, authoring provenance and native approval.

`cinematic_bridge_ascent.py` owns the shared camera, projection, formation,
party/guard phase and acoustic source state. The offline builder is
`tools/build_prologue_bridge_ascent.py`. Retained drawings, guides, prompts,
generation provenance and registration recipes belong under
`assets/source/cinematics/fire_veinhold/bridge_ascent/`; portable exported art
manifests belong under `shot08/characters/` and `shot08/guards/`. The final
`shot08/scene.json` and environment bank describe complete native pictures
with all actors already composited and depth occlusion resolved. Runtime streams
those pictures without an additional decoded source-character bank. Camera
signatures and a separate performance signature bind the bank to the shared rig,
scene, portable art manifests and declared PNG hashes; offline reproduction
also verifies the actual source/export bytes.

The builder now provides `--proof` for native cast checkpoints, `--bake` for
the full normal/Reduced Motion bank, `--verify` for source/output integrity
without rerendering, and `--check` for strict fresh reproduction of all 481
normal and Reduced Motion samples. The final [bake](../../reviews/veinhold_bridge_ascent/logs/bake.log),
[integrity verification](../../reviews/veinhold_bridge_ascent/logs/verify.log) and
[fresh reproduction](../../reviews/veinhold_bridge_ascent/logs/fresh_check.log) pass against the frozen
sources. The [tool catalogue](../../../tools/README.md) records their commands.

An optional temporary environment cache accelerates `--proof` and `--bake`
without supplying a production picture bank. Its 481 views and cached file
hashes have been validated; fresh normal/Reduced Motion RGB and float32 depth
at samples 0, 48, 348 and 480 reproduce exactly. See the
[cache validation record](../../reviews/veinhold_bridge_ascent/render_logs/world_cache_validation.json)
and [render log](../../reviews/veinhold_bridge_ascent/render_logs/world_cache.log).
This is environment evidence only. `--check` always renders from current
sources and cannot use that cache.

The ascent owner reserves eight native image slots, **18.75 MiB** of decoded
pictures plus pending loads, excluding temporary drawing/conversion buffers.
During the final half-second of Shot 7, four incoming ascent slots may coexist
with eight frontal slots: a transient maximum of twelve slots, **28.125 MiB**.
The previous perspective, runner and frontal owners are released before the
ascent expands to its full eight-slot working set. The
[Gallery validation](../../reviews/veinhold_bridge_ascent/gallery/validation.json) records measured cache use,
natural completion and cleanup on return. The
[runtime regressions](../../reviews/veinhold_bridge_ascent/logs/final_tests.log)
cover restart, Skip, focus/pause behavior and cleanup on close.
Reduced Motion retains the same deliberate rise, duration and disclosures; this
path has no shake or roll to remove.

The preservation boundary for this extension is **47 seconds**. Existing
0–47 second picture banks, the twelve existing WAV exports and the 39–47 second
reconstructed PCM remain unchanged. The new audio perspective and one quiet
reinforcement-group export begin at the ascent boundary. The
[preservation/audio record](../../reviews/veinhold_bridge_ascent/preservation_after.json) confirms the
protected picture/WAV hashes, exact earlier PCM and continuous contact phases.
Final focused validation passes **255 unique tests**;
see the [test log](../../reviews/veinhold_bridge_ascent/logs/final_tests.log). The
[Bridge Ascent review](../../reviews/veinhold_bridge_ascent/README.md) binds the
source freeze, native inspection, reproduction and Gallery evidence to this
revision and states which playback was actually inspected.

## Alert and movement audio

A shared reel clock activates both visible red signals and the siren at 30s.
The alarm hold lasts four seconds before the 34s rush. Source light cores are
dimmed when inactive; localized emissive layers make activation perceptible.
Light and smoke projection respects structures and terrain from every angle.

`prologue_alert_audio.py` owns a quiet machinery bed from 25s, the warning,
rush and bridge-settle effects. The machinery recedes with the fortress during
the rush. The near siren continues across the hold/rush boundary, then yields to its
muffled distant version as the camera leaves the fortress. The rush whoosh
occupies 34–35s; bridge wind and a restrained ice creak accompany the settled
view. Existing wind remains continuous. Eagle feather cues are restricted to
the original powered-flight windows and never replay in the new shots.

The 39–42s tracking shot retains the existing siren and wind phases across the
cut. Footfalls come from the runner contact cues, with heavier armored steps
for Lucan and simpler overlapping steps for the other two. Armor/cloth movement
sits near those contacts; the distant warning remains behind the close movement.
Those same clocks continue through the 42–47s frontal shot. Contact phase is
preserved when the viewpoint changes; the face reveal does not restart the
siren, wind loop or runners' step cadence.
Both running shots use the 800 ms cycle; contact cues follow that metadata
rather than preserving the former five-footfalls-per-second cadence. The
running correction's picture/audio preservation boundary is 39 seconds:
the first five shots remain unchanged, while the 39–47s performance and its
contact Foley are retimed together.
A restrained, unvoiced breathing bed starts with the frontal shot to support
the visible effort. It uses the warning channel whose near-siren gain has
already receded to zero; active wind, distant warning and footfalls retain
their owned channels and phase.

For the ascent, the same shared camera and moving source positions
drive footstep, breath, warning and machinery distance/pan rather than a timer
unrelated to the picture. Party movement recedes as the camera rises. One quiet
`reinforcement_group.wav` loop adds distant boot/gear movement from the actual
advancing group centroid; its 2.4-second period retains the guards' 800 ms
cadence without assigning a mixer channel to each guard. This is a thirteenth
export alongside the unchanged twelve existing WAVs. Standalone and full-film
captures use the same global audio timing and camera-derived source positions;
validation and listening/inspection scope are recorded in the
[preservation/audio record](../../reviews/veinhold_bridge_ascent/preservation_after.json).

Pause, focus loss, effects volume, mute, Skip, restart and Gallery close apply
to all owned effects. Standalone clips initialize from their full-reel offset:
the bridge rush starts with the alarm already sounding, rather than replaying
the lead-in. Offline preview audio is reconstructed from those production
exports and timing functions; it is not hardware-loopback listening evidence.

## Gallery and handoff

The Gallery provides the complete entry and eight individual entries, including
**Fire Veinhold — Bridge Ascent**, with representative production thumbnails.
The complete film lasts **55 seconds**; individual durations are **25, 5, 4, 1,
4, 3, 5 and 8 seconds**. Native 60 Hz captures cover the standalone ascent and
complete reel in normal and Reduced Motion, with 480 and 3300 displayed ticks
respectively. The [Gallery record](../../reviews/veinhold_bridge_ascent/gallery/validation.json) reports
natural return, measured cache/lifecycle results and persistent-state isolation.
The disposable, save-disabled runtime preserves parent journey/settings/Continue
state.

Individual previews return directly to the Gallery at their own endpoint.
The complete film continues across the same boundaries without an underlying
bedroom flash, alarm reset or duplicate endpoint hold. New Game retains its
bedroom opening until the complete cinematic and playable infiltration handoff
are ready. No quest, save-schema or mission progression changes belong to this
presentation extension.

See the [Bridge Ascent review](../../reviews/veinhold_bridge_ascent/README.md)
and the [approved 47-second motion-continuity baseline](../../reviews/veinhold_motion_continuity/README.md).
The [running-polish review](../../reviews/veinhold_running_polish/README.md)
records the preceding correction.
The [original frontal-reveal review](../../reviews/veinhold_face_reveal/README.md)
records the superseded 400 ms frontal performance and its earlier cache design.
The [42-second running-shot review](../../reviews/veinhold_bridge_run/README.md)
records the earlier boot-height performance and faction revision.
The [39-second orbit review](../../reviews/veinhold_orbit/README.md) records the
earlier guard/banner palette and film length.
The [eagle-exit review](../../reviews/eagle_exit/README.md) and earlier studies
remain historical evidence of their recorded revisions.
