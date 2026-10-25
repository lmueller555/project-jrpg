# Liam, his parents and Daisy — remaining walk directions

**Left, right and back walks are ready for user review; not yet approved or
merged.** The existing front walks are approved reference animations.

## Enlarged looping comparisons

Each character preview runs front, left, right and back together at the same
10× native scale. All loops have four frames at **140 ms per frame** (560 ms).

- [Liam — all directions](liam_all_directions.gif)
- [Mother — all directions](liam_mother_all_directions.gif)
- [Father — all directions](liam_father_all_directions.gif)
- [Daisy — all directions](daisy_all_directions.gif)

The synchronized family views make relative scale and timing easy to compare:

- [All four walking left](all_left_walks.gif)
- [All four walking right](all_right_walks.gif)
- [All four walking away](all_back_walks.gif)

Individual new directions also have 16× GIFs (`CHARACTER_DIRECTION.gif`) and
10× four-phase contact sheets (`CHARACTER_DIRECTION_frames.png`). Every preview
uses nearest-neighbor enlargement, an opaque light background, an exact shared
GIF palette, infinite looping and full-frame disposal. The floor guide is on
padding row 35, below the sprite art.

## Human motion

The twelve new packs use the approved directional idles and palettes as
read-only appearance inputs. Human frames remain **24×36**; Liam is 26 visible
pixels tall at rest and his parents are 34. The shared humanoid directional
stride supplies legs and arm silhouettes, registered to each character's size.
Heads and shoulders rise together one native pixel on passing poses, preserving
neck length. Profile masks exclude the source character's longer neckline.

Liam retains his green collar, ochre sleeves, short breeches, bare calves and
small boots. His mother keeps the apron on the front/side of her long dress,
only a waistband behind, and her braid on her anatomical right shoulder. The
lower skirt sways one pixel and lifts one pixel on passing poses; the exposed
footwear is brown boot leather rather than bare calves. His father retains the
clay-red tunic, ivory undersleeves, trousers and boots; the buckle is absent in
back view. Profile eyes and closed chins follow the approved faces. Rear views
have no visible eyes.

## Daisy's directional gait

Daisy retains her **32×36** frame and approved gray/white/black coat. Each view
uses its own native idle: the large left-flank patch and smaller right-flank
spots/white hip are not mirrored into the wrong view. Her head and central
markings translate with the body without being stretched. Her floppy ear tips
lag slightly and her fluffy tail moves around a stable overlapping root.

The four-beat order matches the approved front walk: **hind left, fore left,
hind right, fore right**. Exactly one paw lifts two pixels in each phase while
three support. Side-view near paws use row 34 and far paws row 32. Back-view
hind paws use row 34 and forepaws row 32. Planted side paws travel through the
stride instead of remaining at fixed horizontal positions. Native shaggy paw
pixels are reposed around root/knee/toe joints; paws are not replaced with rods.
Daisy remains 23 visible pixels tall in profile and 24 in back at rest, smaller
than Liam. The one-pixel body bob matches the front walk's phase timing.

## Rebuilding and checks

```sh
python tools/build_liam_family_directional_walks.py
python -m unittest discover -s tests -p 'test_liam_family*walks.py' -v
```

Animation JSONs, recipes, four PNG frames and native strips live in each
character's `walk_left/`, `walk_right/` and `walk_back/` directories. Retained
per-phase source layers reconstruct every frame. Daisy's three new directional
joint templates are in `assets/templates/quadruped_32x36/walk_DIRECTION/`.

Eight directional checks cover protected approved inputs, native size/palette/
alpha/baseline/timing, unchanged faces/necks/braid, eye and costume visibility,
quadruped support and paw projection, asymmetric markings, layer/strip
reconstruction, and exact decoded synchronized GIF colors/timing. Together with
the existing front-walk checks, **15 tests pass**. `animations.json` links all
twelve new packs and records SHA-256 hashes of the approved inputs. Rebuilding
preserves each walk's recorded approval status.

This change adds animation assets and review material. Family world placement,
portraits, dialogue and action routines remain future work.
