# Save slots, autosaves and Game Over

Pause offers **Save Game** and **Load Game**. There are ten manual slots;
occupied slots require an explicit overwrite confirmation. Loading during
exploration asks before leaving current progress. The title retains Continue
for the internal resume checkpoint and adds Load Game for choosing a slot.
Entries show location, party levels, playtime and the local save date/time.

Manual slots are never overwritten automatically. Every new journey has its
own autosave history, with Latest, Previous and Earlier generations. Load Game
also lists autosaves from earlier journeys. New Game creates a new journey
identity without deleting existing slots or histories. Before replacing the
resume checkpoint, it archives the previous journey as a loadable **Journey
checkpoint**; an archive failure prevents that replacement. A supported legacy
`journey.json` is copied into the first unused manual slot, leaving the original
checkpoint intact. If all manual slots are occupied, that legacy snapshot is
preserved as a Journey checkpoint instead. Unreadable entries cannot be quick-loaded; earlier readable
autosaves remain available.

## Autosave triggers

- Entering a different exploration scene requests an autosave after its arrival
  and scripted staging settle. Scene-entry autosaves have a 60-second cooldown
  measured during free, focused exploration. Transfers inside that cooldown are
  suppressed, not queued for later. Repeated doorway crossings cannot rotate
  the recovery history. The cooldown survives loading a save.
- A victorious battle requests an autosave after Spoils, rewards and encounter
  completion commit. Required aftermath waits until a stable exploration point.
  Successful escape requests one after resources and return position settle.
  Battle requests bypass the scene-entry cooldown. Victory receipts prevent
  duplicate publication when a settled encounter is replayed on Continue.
- There is no periodic elapsed-time autosave. Pausing, menus, focus loss,
  standing still or pushing against a wall never independently request a save.
- Saves require a living active party member, a clear full player footprint,
  and a short clear route away from the position. Ineligible requests wait for
  valid exploration. This checks placement; it is not a substitute for fixing
  map or collision defects.

The continuous Sanctuary cave is one scene. Moving between its named rooms is
not a scene transfer; its completed battles still autosave.

## Defeat

Ordinary gameplay and Quest Playtests show Game Over automatically after a
short party-defeat presentation. Pause and focus loss freeze that presentation;
Continue can advance directly to the choices. Choices are **Load Last Manual Save**, **Load Last
Autosave**, **Load Game**, and **Return to Title**. Quick loads refer to the
current journey and are unavailable when no readable matching save exists.
Load Game can select a different journey or an older autosave. In a Quest
Playtest, Return to Title returns to the host's quest list.

Defeat grants no rewards, performs no healing or automatic retreat, and never
writes a checkpoint or recovery save. Quit on Game Over also preserves them.
The older boss retry/retreat handlers remain for Gallery playback and historical
checkpoint support; ordinary defeat uses the shared Game Over flow.

## Files and crash safety

The existing `saves/journey.json` remains an internal transaction/resume
checkpoint. Story, item, reward and encounter owners continue using it for
atomic checkpoint/rollback behavior. These frequent writes do not rotate the
visible recovery autosaves. Quit only updates that internal checkpoint.

Manual slots and autosave indices live in `saves/journey_slots/`. Every snapshot
uses the existing bounded, atomic JSON writer. Autosave generations are immutable
files: publish a complete snapshot first, atomically replace its small history
index, then remove the generation that aged out. A failed publication leaves
all referenced previous generations intact. Failed autosaves retry after ten
seconds of eligible exploration without repeatedly rotating history.

Quest Playtests use `saves/playtests/<quest-id>/checkpoint_slots/`, separate
from normal slots, the normal checkpoint, settings and the parent Game's memory.
Save/Load and Game Over work inside their embedded viewport. Their internal
checkpoint store remains disabled: autosaves and manual slots capture validated
snapshots directly. Reopening a playtest can browse its earlier saved sessions.
Headless playtests without a configured parent save path use an isolated memory
library. Gallery playback never publishes saves.

## Validation

Focused suites cover failed writes and manifest publication, all ten slots,
three generations, journey isolation, legacy import, rapid scene crossings,
cooldown restoration, battle requests, invalid placement, corrupt-save fallback,
Game Over, slot loading, overwrite confirmation, and playtest isolation. Existing
battle reward and Continue suites protect the transaction boundary.

A continued reward transaction retains its autosave publication identity.
Explicitly loading a slot starts a fresh attempt within the same journey, so
refighting a boss after rewinding can publish a new recovery save even though
that boss uses the same reward receipt.
