# Iselin native artwork integration

Iselin's live ordinary actor now uses the approved 24×36 native-density idles
and four 16-frame walks, with a 560 ms full cycle. Native scene drawings cover
the seated meal, listening/gesture/turn poses, diagonal travel and aerial views.
The ground cinematic's 80×96 canvas/`[40,92]` anchor and aerial 48×64 canvas/
`[24,56]` anchor retain their camera-specific presentation contracts. They do
not enlarge Iselin's ordinary world/collision footprint.

The central [sprite and animation standard](../../SPRITE_ANIMATION_STANDARD.md)
owns general authoring rules. This review records integration evidence and its
limits rather than introducing another authoring guide.

## Preserved approvals and save compatibility

`approved_assets.json` records **69 PNG hashes** read from immutable Git objects
at pre-integration commit `3bd561af978ae8e1c85d672b696b2ea0c1209753`: four approved
native idles, all 64 approved native walk frames and the unchanged dialogue
portrait. Capture checks those hashes both before and after rendering.

`legacy_escorting_save.json` was created and validated by that pre-integration
runtime using disposable saves and the existing completed-MQ02/escorting-MQ03
fixture. Its old live actor was 21×36 at draw anchor `[10.5,30]`, with a separate
HD presentation. The native runtime successfully Continues that actual older
payload without replaying arrival or changing quest/inventory/player facts.
The new actor uses the approved native `[12,30]` anchor and the same 8×4 probe.
Quest IDs, objectives, authored world coordinates and story outcomes are retained.

## Production captures

`tools/capture_iselin_native_integration.py` renders through **`Game.draw()`**,
including the ordinary world, actual story actor, Gallery and scene controllers.
Every save/settings path is temporary. All PNGs are lossless production frames;
GIF crops add inspection captions and use a common palette. Fixture boundaries
are named in `capture.json`.

- [Front](travel_front.gif), [left](travel_left.gif), [right](travel_right.gif)
  and [back](travel_back.gif): the actual registered Iselin actor follows
  explicit clear review routes through `RegentQuest._move` at 74 world pixels
  per second. Each fixed-camera fixture contains eight idle samples, 64 moving
  samples and eight stopped samples. GIF exposures alternate 30/40 ms, totaling
  2800 ms per route. Full-frame samples use the matching `travel_*.png` names.
- [Pause](pause.png) verifies the real `Game.update` pause path leaves the
  actor's position and animation clock unchanged. [Conversation](conversation.png)
  uses the existing Regent dialogue owner with no objective callback.
- [Meal approach](meal_approach.png), [seated](meal_seated.png) and
  [released](meal_released.png) use the real dining action at staged action
  times. The seated LEFT-facing 24×36 drawing is registered to the actual chair
  at `[12,30]`; hips, feet, table depth and restored ordinary idle were inspected.
- [Aerial gate](arrival_aerial_gate.png), [gate greeting](arrival_gate_greeting.png),
  [gate admission](arrival_gate_admission.png), [relief gesture](arrival_relief.png)
  and [town parking](arrival_town_parking.png) are explicitly selected authored
  shots in the production arrival Gallery. [Diagonal movement](arrival_diagonal.gif)
  samples the actual gate-admission controller over a complete 560 ms interval.
  Existing caravan/horse occlusion remains visible in that shot; it does not
  demonstrate unobscured legs in every frame. The separately labelled
  [exported diagonal sheet](scene_diagonal_frames.png) inspects the full drawn
  anatomy without claiming to be a gameplay screenshot.
- [Paused arrival](arrival_paused.png) accompanies pause/focus clock checks.
  [Sanctuary arrival](sanctuary_clone.png) uses one second of ordinary Gallery
  updates and its real `CastActor` clone of the native live source.
- [Continue](continue_legacy.png) uses the pre-integration saved journey and
  stages only the camera on the restored actor. [Post-rescue report](post_rescue_report.png)
  uses labelled seeded victory/evacuation facts, then the actual dialogue owner
  and acknowledged report. The resulting return-stage snapshot validates.

These captures do not claim a complete played battle, road journey or quest.
The ordinary travel routes and dining/selected-shot times are review staging;
the movement, actor selection, depth sorting, UI and lifecycle paths are real.

## Gallery thumbnails

The two affected Gallery entries were recaptured through the existing
`tools.capture_gallery.capture_thumbnails` API. Their current runtime thumbnails,
per-entry provenance, regional review frames and catalogue contact sheet were
refreshed. `gallery_preservation.json` verifies **27 unrelated runtime thumbnails**
and their per-entry provenance remained unchanged. Regent-arrival's selected
aerial composition happens to reproduce the previous thumbnail bytes; its
per-entry provenance still records the current runtime.

## Reproduction and checks

Run with the project's Pygame/Pillow environment from the repository root:

```sh
python tools/build_iselin_native_actor.py --check
python tools/build_regent_iselin.py --check
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=.:tests \
python -m unittest test_iselin_replacement test_iselin_native_integration
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=. \
python tools/capture_iselin_native_integration.py
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=. \
python -c "from tools.capture_gallery import capture_thumbnails; capture_thumbnails({'regent_arrival','sanctuary_arrival'})"
```

The three replacement checks and five native integration/lifecycle checks passed.
They cover native identity/registration, approach/seated release, Sanctuary
cloning and owner return, immutable approved bytes, real old-save Continue,
pause/conversation selection and Gallery pause/focus/parent isolation. The final
PR records the broader save/MQ03/arrival/rendering validation separately.

Historical pre-integration reviews already documented an active-visit save
fallback failure without its required scene checkpoint and two stale crossroads
region-art fingerprints. This conversion does not repin unrelated historical
art hashes or claim those baseline issues were fixed.
