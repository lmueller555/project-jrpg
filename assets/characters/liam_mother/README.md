# Liam's mother — approved directional idles

Liam's mother is in her **mid-30s**; her name is unassigned. The approved design
uses a chestnut braid, two green eyes, a blue-green dress, cream apron and brown
boots, with empty hands. Hair and eye colors provide resemblance to Liam.

`idle_front.png` is a transparent 24×36 frame, with 14×34 occupied bounds and
foot anchor `[12,34]`. `idle_front.json` records the design, source layers,
eyes and frame registration; `palette.json` records the limited colors.

Build using `python tools/build_liam_family_idles.py`. See the family pack at
`../liam_family/README.md`. The front idle is approved; no world placement or
dialogue has been added.

## Left, right and back — approved

`idle_left.png`, `idle_right.png` and `idle_back.png` retain the approved dress,
apron, chestnut hair, boots and 34-pixel visible height in 24×36 frames. The
braid follows her anatomical right shoulder: near in right profile, largely
obscured in left profile and toward the right in back. Back has a cream apron
waistband over the blue-green dress, with no bow. Profiles have one green eye
and skin-colored chins; back has no visible eyes. Approved front and palette
remain unchanged. `idle_all.png`/`idle_all.json` combine all four views.

Build with `python tools/build_liam_family_turnarounds.py`; see the
[turnaround review](../../../docs/reviews/liam_family_turnaround/README.md).

## Front walk — approved

`walk_front/` adds four shared-stride phases at 140 ms each. Head, shoulders and
braid rise together; the apron/skirt sways subtly, with both boots visible in
all phases. See the [looping review](../../../docs/reviews/liam_family_front_walks/README.md).
