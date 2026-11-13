# Sanctuary cave rescue review

The acknowledged Sanctuary arrival's Caelan/Mira/Lucan rescue continues around
Vespermaw. Confirming the Echo Chamber entry starts the worker discovery and
confrontation. The actual boss ticket is created only after that scene finishes;
retry entry uses the existing short transition. Victory rewards stay with the
boss/CombatEncounters owners. After spoils close, the party frees and treats the
worker, supports him to Greenwell, and offers preparation or evacuation.

Preparation is a temporary safe interval: Lucan remains beside the injured
worker rather than following the player into another fight. Random and optional
elemental encounters resume after the caretaker handoff; ordinary post-Vespermaw
encounters retain their 50% distance-credit reduction. Evacuation begins with an
assisted rise and a short supported walk/fade, then transfers to the Sanctuary.
Lucan leaves the active party only after the caretaker receives the worker.
The existing MQ03 ending/report is not completed by this rescue.

Saved milestones are undiscovered, discovered, confrontation, freed, treated,
greenwell, handoff, and evacuated. Partial unacknowledged actions reconstruct
from their last committed milestone. A failed checkpoint offers retry without
duplicating rewards, changing party resources, or prematurely departing Lucan.
Legacy missing records preserve already-committed battles and departed parties;
noncanonical older cave visits retain their existing boss behavior.

Camera framing follows the call and approach, holds during the warning and
physical work, widens for the reveal, tracks the supported evacuation, and
returns to exploration at Greenwell. Dialogue waits for movement, camera and
minimum action time. Reduced motion uses stable shots and brief masked cuts,
including the longer escort; focus loss and pause freeze camera/action clocks.
Scene bodies, props, lighting and foreground sorting use the production world
renderer. The deposited rock remains at its world station. Dressing remains
attached to the injured worker; tool overlays are removed before travel.

Review artifacts:

- [Full contact sheet](contact_sheet.png) and [animated sequence](rescue.gif).
- [Discovery](call.png), [examination](examine.png), [Vespermaw reveal](reveal.png).
- [Lifting before release](free_worker.png), [after release](free_worker_after_cue.png),
  [treatment after its cue](treatment_after_cue.png),
  [assisted standing](assisted_stand_after_cue.png).
- [Greenwell rest](greenwell_waiting.png), [departure choice](departure_choice.png),
  [supported departure](departure_walk.png),
  [caretaker receiving](caretaker_receives_after_cue.png),
  [completed handoff](caretaker_handoff_finished.png).
- `evidence.json` records camera/actor samples and source/output fingerprints.
  `validation.json` records test selection and its limits.

Captures use a disposable embedded Game with disk persistence disabled. Earlier
quest/arrival prerequisites and a durable Vespermaw victory are explicitly seeded;
this is not a played fight or a full quest walkthrough. No combat EXP is granted
by the visual fixture. Party resource snapshots are checked unchanged across the
rescue. The GIF follows the minimum playback clocks with brisk dialogue input;
The 480×320 GIF samples every 500 ms with nearest-neighbor reduction and a
shared review palette; its duration is 71 seconds. PNG frames remain
authoritative for colors and detail.

Visual review inspected discovery/reveal framing, actor facing and body scale,
rock lifting and deposition, dressing/tool cleanup, supported travel spacing,
Greenwell ownership, and the caretaker receive gesture. The numbered cue-after
stills supplement the phase samples. These pictured phases do not certify every
unrelated Sanctuary interaction or ambient NPC.

Reproduce with:

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  python tools/capture_sanctuary_rescue.py
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=tests \
  python -m unittest test_sanctuary_rescue
```
