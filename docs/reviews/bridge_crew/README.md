# Bridge crew gameplay review

New poses and props have **review** status. Existing villager appearances,
source layers and walks retain their existing approvals. See the precise
[art provenance](../../../assets/source/characters/bridge_workers/README.md).

The videos are production `Game.update` / `Game.draw` at normal 2× display scale,
960×640, 30 simulation updates and 15 encoded frames per second. There are no
painted overlays or alternative scene renderers. Captured frames were inspected
for feet, stone grip, cup release/placement/handoff, seated alignment, depth and
safe separation from the river. The first view was also checked before adding
actors, to retain the existing regional scale.

- [Work and full tea scene](work_and_tea.mp4): finite sorting, opt-in visit,
  both exchanges, moving the cup, handoff, sitting, tool takeover and return.
- [Blocked route and Continue](blocked_and_continue.mp4): worker yields to the
  player's actual collision probe, recovers after movement, then resumes after
  Continue with one committed stone kept in its stack.
- [Tea interruption / Continue](tea_continue.mp4): reload during the cup handoff
  and again during sitting. The completed exchange stays read; the physical
  break resumes and the cup returns to its kettle.

The capture fixture instantiates the real game with temporary saves, mutes
sound, seeds prior quest completion using the existing lantern capture helper,
and explicitly places Caelan at the work area. It does not simulate a full
walk from town or full playthrough of those quests. The camera remains fixed
on the work area. E interactions and page advances are scripted; no routine
stage is forced in the first two clips. The third clip starts from the valid
completed-sorting checkpoint to isolate tea recovery. The blocked-path clip
explicitly places Caelan in the lane, then uses ordinary movement to clear it.
Continue uses the game's real save/title restoration. The open current-errand
panel is a fixture artifact, not a newly added bridge objective.

Reproduce with `python tools/capture_bridge_crew.py`. Durations and bounded cache
statistics are in [capture_report.json](capture_report.json). No audio belongs
to this PR; localized sound is a separate planned change.

The tea visit uses E to begin and again at each dialogue boundary. This keeps
the physical vignette optional and permits walking away without automatically
starting dialogue. Saves retain completed physical beats rather than every
animation frame; an unfinished movement restarts from its last safe station.
