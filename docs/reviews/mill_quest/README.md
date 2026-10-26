# A Little Trouble at the Mill

[Complete quest overview](quest.gif) · [Small spell close-up](small_spell.gif) · [Slow motion](small_spell_slow.gif)

The capture runs the production game through Mira's recruitment, the mill
investigation, the upstream trail, intake preparation, Caelan's successful small
spell, Mira's encouragement, their cooperative repair and the final return to
Halden. The restored wheel is verified before the closing exchange completes
MQ02.

The overview is a compact, time-compressed review. It retains every dialogue
page and scene transfer, with sparse samples of navigation and physical actions.
Dialogue pages are held for readability. The separate spell close-ups show the
actual action at approximately 15 fps and at half that playback speed. Review
captions sit outside the game image. PNG stills retain the game's full UI size.

Only completed MQ01 prerequisites, the earlier optional Venn spell failure and
the initial workbench standing spot are seeded. All MQ02 progress comes from
real dialogue callbacks, collision-aware player walking, the same Mira actor,
public outdoor trail transfers and the production action clocks. The script
never sets MQ02 objectives or repair milestones directly. It checks completion
and the running mill at the end. GIF exports use a shared palette; decoded
frames and cumulative duration are verified.

## Key moments

- [Stopped mill](mill_stopped.png)
- [Obstructed upstream intake](upstream.png)
- [Caelan's small success](small_success.png)
- [Mira's encouragement](encouragement.png)
- [Cooperative physical repair](cooperative_repair.png)
- [Restored intake](intake_restored.png)
- [Running mill](mill_running.png)
- [Closing exchange](resolution.png)

The spell moves a shallow pocket of still water into the adjacent drain after
Mira has relieved the intake pressure. The main stream remains outside Caelan's
control. The cleared recess stays visible. The capture checks that the intake screen,
lever and millrace stay in their prepared state after the spell. During the
physical repair, Mira
works the mechanism while Caelan assists through the connected rope.

The review run uses the earlier-failure dialogue branch. Players who chose tools
at the Venns receive encouragement without a reference to an unseen failure.
Both histories are covered by the quest tests.

Rebuild the capture with:

```sh
python tools/capture_mill_quest.py
```

Pygame and Pillow are required. SDL dummy video and audio drivers allow the
script to run without a visible window. The quest and its saved checkpoints are
documented in [MILL_QUEST.md](../../MILL_QUEST.md).
