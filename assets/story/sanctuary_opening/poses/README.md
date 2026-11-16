# Sanctuary opening poses

Caelan uses complete drawn 2× action keys (48×72 artwork; 24×36 logical),
exported by `python tools/export_caelan_scene_actions_hd.py`. Sleep/wake,
sit/stand, eating and the courteous cup pass retain scene timing, logical
anchors and ownership cues. The cup pass extends toward the table; it is not a
drinking action. The cup remains a separate owned prop.

`python tools/build_sanctuary_opening_poses.py` restores unchanged Tomas/props
from retained source inputs and invokes the Caelan exporter. The older Caelan
body-part assembly is removed. Construction and interaction rules live in
`docs/VISUAL_ART_STANDARD.md` and `docs/OBJECT_INTERACTION_STANDARD.md`.
