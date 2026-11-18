# Live HD sanctuary gardener

The existing sanctuary gardener now uses `adult_woman_02`: same chestnut
hair, sage clothing and recognizable civilian identity while resting,
walking and working. This is not the separate kitchen gardener in Elden Vale.

[In-game native sequence](live_sequence.png) captures the real town renderer
during one uninterrupted routine. It shows the same actor from pail pickup
through attachment, lowering, raising, retrieval, loaded travel and watering.
The normal and slow source-art loops below are isolated pose proofs, not a
substitute for in-game rendering.

| Pose bank | Normal | Half speed |
| --- | --- | --- |
| Loaded profile carry | [GIF](carry_full_left.gif) | [GIF](carry_full_left_slow.gif) |
| Crank | [GIF](well_crank_left_.gif) | [GIF](well_crank_left__slow.gif) |
| Water the flowers | [GIF](pour_left.gif) | [GIF](pour_left_slow.gif) |

The runtime uses the roster's directional walks between crank and loading
positions, when the well owns the pail. Carrying, cranking, hooking, catching
and pouring use 98 registered native-density body frames. The old action
manifest is the timing and registration reference, and the same pail asset
bank is shared by the body renderer and the well. Actor ID, route, physical
probe, draw anchor, transfer phases, and six-bed watering order are unchanged.
No new dialogue was added; the actor exposes the roster's matching portrait.

Rebuild the native action art and capture the live sequence from the repo root:

```sh
python assets/source/characters/npc_roster_hd/adult_woman_02/gardener_hd/export.py .
python tools/capture_gardener_hd.py
```
