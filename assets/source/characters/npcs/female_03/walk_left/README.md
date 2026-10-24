# Female NPC 03 — left-walk palette parts

Status: approved by the user in chat.

`parts/` retains exact recolors of the approved blue base's head/bodice appearances and all posed compositing layers. The frame metadata gives their order and paths from the repository root. Recomposition matches each native frame exactly.

Rebuild using `python tools/build_female_npc_walk_variants.py --direction left`. The helper reads the approved base animation, the shared female palette variant configuration, and this palette's approved idle eye landmarks. It swaps named hair/dress colors and the iris color across entire native frames and parts, covering raised shoulders and swinging skirts without moving any pixels. Source skin, outline, boots, alpha and pose data stay unchanged. Back heads introduce no eyes.

The character recipe records the full color replacement map, base animation, retained costume poses and palette source. Approval status comes from that recipe and survives rebuilds. Use `--direction all` to refresh all comparisons as well.

The profile head now includes the three-pixel closed-mouth jaw cleanup from the directional appearance exporter; this appearance revision is awaiting review.
