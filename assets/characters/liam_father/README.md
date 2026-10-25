# Liam's father — approved directional idles

Liam's father is in his **mid-30s**; his name is unassigned. The approved design
uses dark brown hair, a short beard, two hazel eyes, a clay-red tunic over ivory
sleeves, a plain belt, dark trousers and brown boots, with empty hands.

`idle_front.png` is a transparent 24×36 frame, with 16×34 occupied bounds and
foot anchor `[12,34]`. `idle_front.json` records the design, source layers,
eyes and frame registration; `palette.json` records the limited colors.

Build using `python tools/build_liam_family_idles.py`. See the family pack at
`../liam_family/README.md`. The front idle is approved; no world placement, walks
or dialogue have been added.

## Left, right and back — approved

`idle_left.png`, `idle_right.png` and `idle_back.png` retain the approved dark
hair, short beard, clay-red tunic, ivory undersleeves, dark trousers and boots.
Visible height stays 34 pixels in 24×36 frames. Profiles have one hazel eye;
back has no eyes or belt buckle. The approved front and palette remain
unchanged. `idle_all.png`/`idle_all.json` combine all four views with independent
approval status.

Build with `python tools/build_liam_family_turnarounds.py`; see the
[turnaround review](../../../docs/reviews/liam_family_turnaround/README.md).
