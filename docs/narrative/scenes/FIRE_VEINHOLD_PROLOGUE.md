# Fire Veinhold prologue — cinematic production

**Status:** Shot 1 is implemented as a 25-second Gallery presentation: a
15-second summit approach followed by ten seconds overlooking the Cinder Isles.
Shots 2–5 await their own implementation. Further scenes follow the overhead
bridge view; the final playable handoff remains open.

[Chapter 1](../game_01/CHAPTER_01.md) owns the opening story. This document owns
cinematography and implementation. The [sprite standard](../../SPRITE_ANIMATION_STANDARD.md)
owns artwork construction. The [Cinder Isles guide](../world/POLAR_REGIONS.md#cinder-isles)
owns the approved geography; the canonical world map remains unchanged.

## Shot order

| Shot | Duration | Picture and disclosure |
| --- | --- | --- |
| 1 — Eagle Ascent and Cinder Isles | 25 seconds | Follow the eagle east-southeast over Merovar's coastal summit for 15 seconds, then retain a clear offshore volcanic vista for ten seconds. No fortress close-up or cast reveal yet. |
| 2 — Volcano and Veinhold | 15 seconds, future implementation | Closer establishing view of the volcano, military fortress and reservoir drawing Fire-aspected aether. Red alert lights already signal an emergency before the infiltrators appear. |
| 3 — Running legs | 3 seconds, future implementation | Side tracking of Iselin, Lucan and the Crown soldier running over a metal fortress access bridge. |
| 4 — Faces | Exact duration open | Track backward in front of the runners and pan down to reveal faces. Lucan leads in the center. Iselin is on his anatomical right, close behind (screen left); the soldier is on his anatomical left (screen right), about ten feet behind. |
| 5 — Bridge ascent | 8 seconds, future implementation | Rise over Lucan into a rapidly ascending overhead view. Frozen guards lie behind the party; more guards approach from the fortress. This does not finish the cinematic or define the gameplay handoff. |

The fortress access bridge is distinct from Elden Vale's western bridge.
The revised Shot 1 introduces the island geography before the closer facility
view. Its ten-second vista is additional to the fifteen-second ascent.

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
  push preserves the composition while the eagle flies onward and recedes.

A single tall opaque painting contains the summit approach, coastal descent,
open sea and islands. The camera's source window pans upward from the rocky
approach into the upper vista. Every geographic landmark shares one transform;
there are no independently scrolling foreground/background mountain groups,
terrain-card seams, panorama cross-fades or hard cut at the crest. At 15s the
upper vista is fully framed; the nearer mainland ridge has passed below the
main view. The eagle occupies the lower sea corridor, leaving the main crater
visible, then becomes smaller as it travels toward the islands.

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
the future fortress, reservoir and military infrastructure. Its volcano is
inactive because the Veinhold is extracting Fire-aspected aether: no glowing
crater, lava flows or eruptive fire remain. It still releases light steam/gas.
The distant volcano retains its active glow and a denser ash plume. Othara's
Damar Drylands remain a separate landmass.

Two large steel bridges are visible. The nearer bridge runs from Merovar's
rocky mainland coast to the main island's front terrace. The farther bridge
runs from the Damar headlands on the left to the island's rear-west approach.
Both have complete abutments, steel decks and piers scaled to perspective.
The final source window begins at y50 so the nearer Merovar landing remains
visible along with the island and both volcanoes. The approved
Fire Veinhold site is on the main island near the volcano; the fortress and
reservoir receive their closer reveal in Shot 2. Exact distances, travel
times, facility coordinates and the infiltration party's route remain open.
The world map is illustrative and supplies relationships rather than a precise
bearing grid or guaranteed real-world line of sight.

## Art and runtime contract

The implemented shot list is `assets/story/fire_veinhold_opening/scene.json`.
The shot explicitly records `ascent_duration:15`, `vista_duration:10`, and
`duration:25`. Durations must be positive, finite and sum correctly. Future
storyboard rows are not runtime placeholders.

The native picture remains **960×640**, full **3:2**, rendered directly to the
actual UI surface. The new opaque panorama is **1024×1536**, with vertical
overscan for the climb. Its source, references, prompt, hash and export framing
are retained under `assets/source/cinematics/fire_veinhold/shot01/environment/`.
`tools/build_prologue_mountains.py --check` verifies reproduction.

The eagle retains its complete 256×256 drawings, density two, chest anchor
[128,144], and 750ms powered-wing cycle. Animation follows real elapsed time:
extending the shot does not slow its wing cadence. The bank spans three seconds.
The second powered window ends at 13.25s on the shared neutral wing pose.
Whole-body scale during the vista represents increasing distance; changing wing
bounds never drive registration or body proportions. Reduced Motion lowers
lateral sway while retaining the same phase durations, wings and geographic
reveal. Focus/pause freeze the entire presentation.

Wind continues across the crest and through the ten-second vista. The crest
rush is cued at 14.65s; feather Foley follows actual powered downstrokes only.
Audio leases respect effects volume, mute, focus and cleanup without stealing
music channels. The audio source folder retains its deterministic export recipe
and CC0 Foley attribution. Preview movies reconstruct audio from those exports
and cue metadata, rather than claiming hardware-loopback listening review.

## Animated volcanic plumes

The revised panorama contains no painted smoke plumes. `cinematic_smoke.py`
composites textured billows from both crater mouths in source-art coordinates,
using the same scale and origin as the terrain. Billows rise, expand, drift
with varied turbulence, and fade continuously; the main vent uses light steam
and the distant vent denser ash. One complete authored cloud from the generated
VFX sheet is cropped and exported as `smoke_puff.png`; scaling and alpha over
each particle's life supply the motion. This is a particle effect, not a
creature animation assembled from body parts.

The particle samples are pure functions of shot time and deterministic seeds.
The plumes are prewarmed, remain bounded after seeks, and freeze with pause or
focus loss. Restart reproduces the same initial state. Reduced Motion lowers
lateral drift/turbulence without freezing the plumes. Texture and emitter
configuration live in the environment recipe/export manifest; malformed or
unbounded values fail before playback. The source atlas, exact prompts and
hashes are preserved. The wider island and bridges remain in the single
opaque landscape, retaining consistent geographic movement.

## Gallery and handoff

Both **Shot 1 — Eagle Ascent and Cinder Isles (25s)** and **Fire Veinhold —
Complete Cutscene** use the same production controller. The complete entry
currently contains this 25-second shot. Future implemented clips populate their
own Gallery entries and extend the complete entry from the same ordered list.
The normal controls, disposable save-disabled runtime and unchanged parent
save/settings/Continue boundaries remain in force.

At 25s an isolated replay returns directly to the Gallery. There is no black
end fade. The terminal camera, eagle and wind state is exposed for later clip
integration. New Game retains its bedroom opening until the full cinematic and
playable infiltration handoff are ready.

See [current review evidence](../../reviews/cinder_bridges_smoke/README.md).
Earlier ten-second studies remain historical evidence of their own revisions.
