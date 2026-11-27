# Fire Veinhold prologue — cinematic production

**Status:** The Gallery presentation contains six production shots totaling
42 seconds: the existing 25-second summit approach/vista, a five-second island
orbit, four-second alarm lead-in, one-second bridge rush and four-second frozen
guard reveal, followed by three seconds tracking the running party's legs.
The frontal face reveal, overhead ascent and final playable handoff remain
future implementation.

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
| 7 — Faces | Exact duration open, future implementation | Track backward and pan down to faces. Lucan leads in the center. Iselin is on his anatomical right, close behind (screen left); the Crown soldier is on his anatomical left (screen right), about ten feet behind. |
| 8 — Bridge ascent | 8 seconds, future implementation | Rise over Lucan into an ascending overhead view. Frozen guards lie behind the party; more guards approach from the fortress. The final gameplay handoff remains open. |

The fortress access bridge is distinct from Elden Vale's western bridge. The
five-second orbit replaces the previously proposed separate 15-second closer
fortress shot. Later party shots are storyboard direction, not runtime
placeholders. There is no cast reveal or new dialogue in Shots 2–5. Shot 6
reveals their lower-body movement before the later frontal reveal.

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

The implemented shot list is `assets/story/fire_veinhold_opening/scene.json`.
The shot explicitly records `ascent_duration:15`, `vista_duration:10`, and
`duration:25`. Durations must be positive, finite and sum correctly. Future
storyboard rows are not runtime placeholders.

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
in motion, preceding the separately planned frontal face reveal.

Lucan leads. Iselin follows close on his anatomical right, nearest this camera;
the Crown soldier remains on his anatomical left, 3.048 metres (ten feet)
behind. The framing can admit the trailing soldier near its edge rather than
compressing that gap. Depth ordering follows those lanes and foreground bridge
members, with no duplicate body or equipment overlays.

Each runner uses complete authored drawings with both near and far legs resolved
in the source pose. Contact, compression, push-off, flight and recovery must
progress through the cycle with a coherent loop seam. Foot contact metadata
drives the corresponding metal footfalls. Each production cycle has 24 complete
poses over 400 ms, advancing one pose at every 60 Hz display tick. Lucan starts
at pose 0; Iselin is offset five ticks and the Crown soldier nine ticks. These
phase differences keep their steps from becoming a synchronized march.
World travel and scenery motion use an approximate source-floor fit;
this calibration is staging evidence, not a claim of perfect pixel-level foot
locking throughout every authored pose. Simply accelerating a walk,
sliding a whole idle or rotating detached limbs cannot supply this performance.
Cloth and armor movement follow the same authored phase.

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

Pause, focus loss, effects volume, mute, Skip, restart and Gallery close apply
to all owned effects. Standalone clips initialize from their full-reel offset:
the bridge rush starts with the alarm already sounding, rather than replaying
the lead-in. Offline preview audio is reconstructed from those production
exports and timing functions; it is not hardware-loopback listening evidence.

## Gallery and handoff

The complete entry and all six individual entries use the same production
controller and ordered scene manifest. The complete film lasts **42 seconds**;
individual durations are **25, 5, 4, 1, 4 and 3 seconds**. Each entry has its own
representative production thumbnail. The Gallery's disposable, save-disabled
runtime preserves parent journey/settings/Continue state.

Individual previews return directly to the Gallery at their own endpoint.
The complete film continues across the same boundaries without an underlying
bedroom flash, alarm reset or duplicate endpoint hold. New Game retains its
bedroom opening until the complete cinematic and playable infiltration handoff
are ready. No quest, save-schema or mission progression changes belong to this
presentation extension.

See [current running-shot and faction review evidence](../../reviews/veinhold_bridge_run/README.md).
The [39-second orbit review](../../reviews/veinhold_orbit/README.md) records the
earlier guard/banner palette and film length.
The [eagle-exit review](../../reviews/eagle_exit/README.md) and earlier studies
remain historical evidence of their recorded revisions.
