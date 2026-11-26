# Fire Veinhold prologue — cinematic production

**Status:** Shot 1 implemented as a Gallery presentation. Shots 2–5 are approved
cinematography awaiting their own implementation PRs. Additional shots follow
the overhead bridge view; the sequence's ending and playable handoff are open.

[Chapter 1](../game_01/CHAPTER_01.md) owns the infiltration and opening-act story.
This document owns this cinematic's staging, timing and production contracts.
The [sprite standard](../../SPRITE_ANIMATION_STANDARD.md) owns asset construction.
No former flashforward, relief-caravan scene or festival is restored.

## Approved shot order

| Shot | Duration | Picture and movement | Sound and disclosure |
| --- | --- | --- | --- |
| 1 — Eagle Ascent | 10 seconds | Follow an eagle flying quickly uphill through alpine rock spurs to the summit. The camera follows from above and behind; near rock faces pass rapidly while distant ranges hold their scale. | High-altitude wind and close feather/downstroke sounds. No dialogue or facility alarm yet. |
| 2 — Volcano and Veinhold | 15 seconds | Crest into a huge establishing view of the volcano, military fortress and reservoir drawing Fire-aspected aether. | Red alert lights are already active during the reveal, establishing an emergency before the infiltrators appear. Detailed audio staging belongs to that shot's PR. |
| 3 — Running legs | 3 seconds | Side tracking shot of Iselin, Lucan and the Crown soldier's legs running over a metal fortress access bridge. | Metal footfalls and equipment movement; exact mix is future work. |
| 4 — Faces | Exact duration open | Track backward in front of the runners and pan down to reveal their faces. Lucan leads in the center. Iselin is on his anatomical right, close behind (screen left in this view); the soldier is on his anatomical left (screen right), about ten feet behind. | Exact performance and transition timing remain to be authored. |
| 5 — Bridge ascent | 8 seconds | Move up over Lucan's head into a rapidly ascending top-down view of the long bridge leading into the Veinhold. Several guards are already frozen behind the party; more guards come out of the entrance toward them. | The emergency continues. This is not the end of the cinematic or a decided gameplay handoff. |

The bridge is a fortress access structure, distinct from Elden Vale's western
bridge. Shot 1 does not show the volcano, Veinhold, reservoir, alert lights,
frozen guards or party early. The exact facility location and mountain name
are not established by this scenery.

## Shot 1 performance

The shot starts already in the final high-altitude approach rather than
attempting a ground-to-summit climb in ten seconds. Dawn light catches slate
rock, sparse alpine vegetation and small snow remnants; this is not a depiction
of Adamanthra's later Ice Dome.

- **0–2s:** Powered flight between nearby rock spurs.
- **2–5s:** A shallow bank and recovery through the approach, preserving a
  readable complete body and a stable chase distance.
- **5–8s:** Another powered climb.
- **8–10s:** Level-wing glide over the final crest. The near ridge falls below
  the camera and the view opens beyond it.

The camera retains forward and upward velocity at ten seconds. There is no
ease to a stop, black fade or implied ending. Its terminal pose, velocity,
eagle registration/phase, depth-layer offsets and wind playhead are exposed by
`FireVeinholdOpening.handoff_state` for Shot 2. For now the isolated Gallery
presentation returns directly to its catalogue when the ten seconds finish.

## Artwork and rendering

`assets/story/fire_veinhold_opening/scene.json` is the ordered implemented-shot
list. Only completed shots go here; future storyboard rows above are not blank
runtime clips.

The picture is composed at **960×640** in the game's full **3:2** frame. Its
six independently authored mountain layers are native **1448×1086** RGBA/sky
images, with separate depth/framing. The eagle uses complete **256×256** frames,
density two, registered at the chest **[128,144]**. Wing extent never changes
body scale. No detached-wing rig or warped idle constructs the flight poses.

The eagle's 16-frame powered cycle lasts **750ms**. Its first and second
powered windows enter at **391ms** and **141ms** respectively so the two glides
and bank share the same level-wing boundary pose. Eight complete bank poses
span three seconds including the shared neutral entry/exit; the glide retains
level wings. Inspect loop seams, head/chest/tail registration and both wings at
normal and reduced playback speed; export checks alone do not certify motion.

`FireVeinholdOpening.draw` sends the detailed picture directly to the actual UI
surface before drawing pause/skip controls. It does not enlarge an already
reduced 480×320 world image. A downsampled logical copy exists for legacy debug
consumers; Gallery thumbnails and dedicated captures use the detailed renderer.
Full frame aspect is preserved at all output sizes.

Foreground cards remain in their authored depth order with their lower source
edges below the picture. The camera never reveals a rectangular terrain-card
bottom or introduces a new ridge abruptly halfway through the shot. Reduced
Motion lowers lateral camera sweep and removes the fast closest foreground
passes; ascent, complete wing animation and the ten-second duration remain.

Preserved generation sources, exact prompts, hashes, registration and recipes:

- `assets/source/cinematics/fire_veinhold/shot01/environment/`
- `assets/source/cinematics/fire_veinhold/shot01/eagle/`
- `assets/source/audio/fire_veinhold/shot01/`

Rebuild/check with `tools/build_prologue_mountains.py`,
`tools/build_prologue_eagle.py` and the audio source folder's recorded command.
These exporters handle sampling, alpha and registration; they do not synthesize
new creature anatomy or redraw terrain procedurally.

## Audio and lifecycle

The stereo mountain wind is a seamless offline-generated loop, with distinct
near pass, bank gust, climb rush and crest gust cues. Soft retained CC0 Foley
marks actual downstrokes in powered flight only. No eagle screech, human
dialogue, alarm or Fire reservoir sound belongs to this first shot. There is
no newly selected score.

`PrologueFlightAudio` leases available mixer channels without resizing the
mixer or stealing music. Effects volume, mute, pause, focus, replay and close
apply to its own sounds. `begin_shot` resets local cues while retaining the wind
channel for a following compatible clip; final Gallery completion releases it.
Offline preview audio is a reconstruction of authored cues, distinct from a
live hardware listening capture.

## Gallery and integration

The **Fire Veinhold Prologue** section has:

- **Fire Veinhold — Complete Cutscene** (`fire_veinhold_opening`): all implemented
  clips in the scene's ordered list. Currently ten seconds.
- **Shot 1 — Eagle Ascent (10s)** (`fire_veinhold_shot_01`): only `eagle_ascent`.

The registry derives individual entries from the same list. Each future shot
PR adds its renderer/assets and scene record, thumbnail and validation; the
complete entry then includes it automatically. It must preserve the preceding
shot's intended cut or continuous handoff and its audio cleanup.

Both entries use the same production controller in disposable, save-disabled
Gallery games. Pause/focus freeze the scene clock; restart recreates the shot;
skip/natural completion return without showing the bedroom or starting a quest.
Continue, party/inventory facts, settings and saved journey bytes remain intact.

New Game deliberately retains the current bedroom morning until the full
opening cinematic and its playable infiltration handoff are ready. This first
shot does not implement the infiltration, scripted defeat or later attack.

See [review evidence](../../reviews/fire_veinhold_opening/README.md) for captures,
commands, verification and remaining production scope.
