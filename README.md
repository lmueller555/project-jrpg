# Project JRPG

The project is starting over from its story. The previous implementation, maps, assets, art specifications, tools, tests, and build workflows have been removed. There is currently no runnable game. New asset tooling is documented below.

## Story documents

- [Foundational lore](docs/FOUNDATIONAL_LORE.md): cosmology, ancient history, and established worldbuilding.
- [Saga bible](docs/narrative/saga/SAGA_BIBLE.md): overarching narrative and multi-game boundaries.
- [Revelation plan](docs/narrative/saga/REVELATION_PLAN.md): player knowledge and disclosure constraints.
- [Game I story bible](docs/narrative/game_01/STORY_BIBLE.md): game-level requirements and an earlier alternative premise.
- [Game I act outline](docs/narrative/game_01/ACT_OUTLINE.md): the proposed direction, *The Broken Covenant*.
- [Chapter 1: Life in Eldenmere](docs/narrative/game_01/CHAPTER_01.md): approved opening structure.
- [Opening quest: A Day Like Any Other](docs/narrative/game_01/CH01_MQ01.md): approved first-quest narrative and dialogue.

These documents retain their original status labels. Approved story decisions, proposals, and open questions remain distinct; the reset does not change narrative canon.

## New character art

[Caelan's idle sprites](assets/characters/caelan/README.md) begin the new art library at 24×36 pixels per frame. All four directional idle designs are approved.

The approved [front-facing walk cycle](assets/characters/caelan/walk_front/README.md) contains four frames with coordinated head-and-shoulder bobbing and an enlarged looping GIF.

Matching [left](assets/characters/caelan/walk_left/README.md), [right](assets/characters/caelan/walk_right/README.md), and [back](assets/characters/caelan/walk_back/README.md) walking cycles are approved. The [combined looping preview](assets/characters/caelan/walk_directions_review.gif) shows all four approved directions together.

[Mira's design](assets/characters/mira/README.md) is approved: dark brown ponytail, cream flower, pink working shirt, charcoal trousers, boots, and tool pouch. Her front idle sprite is available for review at the same 24×36 scale, with shared pose components and editable assembly layers.

Her [front walking animation](assets/characters/mira/walk_front/README.md) is approved. It is assembled from character-specific parts and the shared Caelan pose template using the [repeatable asset builder](tools/README.md).

Her [left](assets/characters/mira/walk_left/README.md), [right](assets/characters/mira/walk_right/README.md) and [back](assets/characters/mira/walk_back/README.md) walks and new facing appearances are approved. The [combined looping preview](assets/characters/mira/walk_directions_review.gif) shows all four directions together.

The first [generic male NPC](assets/characters/npcs/male_01/README.md) front idle is approved: brown hair, a moss-green shirt, tan trousers and brown boots. Both additional palette variants are approved: [black hair, rust shirt and charcoal trousers](assets/characters/npcs/male_02/README.md), and [gray hair, slate shirt and brown trousers](assets/characters/npcs/male_03/README.md). The [enlarged comparison](assets/characters/npcs/male_variants_review.png) shows all three. These start the planned set of two NPC base designs with three palette variants each.

All three male NPC palettes have approved front, left, right and back stationary idles at 24×36. The [directional comparison](assets/characters/npcs/male_idle_directions_review.png) shows variants as rows and front, left, right, back as columns. All twelve directional idle frames are approved. All three palettes also have approved walking cycles in all four directions.

The base male NPC's [four-frame front walk](assets/characters/npcs/male_01/walk_front/README.md) is approved. It uses the shared stride, tan-trouser/brown-boot colors and coordinated head-and-shoulder bob. The [enlarged looping preview](assets/characters/npcs/male_01/walk_front/walk_front_preview.gif) plays all four frames at 140 ms each.

The [rust/charcoal](assets/characters/npcs/male_02/walk_front/README.md) and [slate/brown](assets/characters/npcs/male_03/walk_front/README.md) front-walk variants are approved. The [synchronized comparison](assets/characters/npcs/male_walk_front_variants_review.gif) shows all three palettes using the same stride, timing and bob.

The base male NPC's [left](assets/characters/npcs/male_01/walk_left/README.md), [right](assets/characters/npcs/male_01/walk_right/README.md) and [back](assets/characters/npcs/male_01/walk_back/README.md) walking cycles are approved. The [four-direction looping preview](assets/characters/npcs/male_01/walk_directions_review.gif) includes the approved front walk for comparison. The other palette walks use these approved base cycles.

The rust/charcoal and slate/brown left, right and back walks are approved. The [complete synchronized grid](assets/characters/npcs/male_walk_all_variants_review.gif) shows directions as rows and palettes as columns. Enlarged comparisons are also available for [left](assets/characters/npcs/male_walk_left_variants_review.gif), [right](assets/characters/npcs/male_walk_right_variants_review.gif) and [back](assets/characters/npcs/male_walk_back_variants_review.gif). All twelve male NPC walking cycles are approved.

The first [female NPC front idle](assets/characters/npcs/female_01/README.md) is approved: dark hair in a low bun, a blue calf-length dress with short sleeves and brown ankle boots, at the same 24×36 scale. The [enlarged preview](assets/characters/npcs/female_01/idle_front_review.png) and [scale comparison](assets/characters/npcs/female_01/scale_comparison.png) show the approved design. All four directional idles and all four blue base walking cycles are approved.

All three female front-idle palettes are approved: dark hair/blue dress/blue eyes, auburn hair/sage dress/green eyes and blonde hair/plum dress/hazel eyes. The [enlarged comparison](assets/characters/npcs/female_variants_review.png) shows the same silhouette across all three; [eye close-ups](assets/characters/npcs/female_eyes_review.png) show the pupil and iris differences.

The [female directional review](assets/characters/npcs/female_idle_directions_review.png) shows all three palettes as rows and front, left, right, back as columns. All twelve directional idles are approved, with a visible low bun, the shared row-28 dress hem and exposed ankle boots. Profiles have one blue, green or hazel iris accent; back views show no eyes. [Profile close-ups](assets/characters/npcs/female_profile_eyes_review.png) compare those iris colors.

The blue base female NPC has an approved [four-frame front walk](assets/characters/npcs/female_01/walk_front/README.md), using the shared stride and coordinated bob with dedicated dress poses. The [20× looping preview](assets/characters/npcs/female_01/walk_front/walk_front_preview.gif) shows the one-pixel skirt sway, passing hem lift and visible ankle boots. This cycle is approved; palette variants and other walking directions will use its timing and dress motion.

The blue female NPC has approved [left](assets/characters/npcs/female_01/walk_left/README.md), [right](assets/characters/npcs/female_01/walk_right/README.md) and [back](assets/characters/npcs/female_01/walk_back/README.md) walks. The [four-direction looping preview](assets/characters/npcs/female_01/walk_directions_review.gif) includes the approved front cycle for comparison. All four cycles are approved and preserve the bun, profile eye, coordinated bob, dress hem motion and visible ankle boots.

The [sage/green-eye](assets/characters/npcs/female_02/README.md) and [plum/hazel-eye](assets/characters/npcs/female_03/README.md) walking palettes are approved in all four directions. They preserve every approved blue-base pose and timing. The [complete synchronized grid](assets/characters/npcs/female_walk_all_variants_review.gif) shows front, left, right and back as rows; blue, sage and plum as columns. Larger three-palette comparisons are available for [front](assets/characters/npcs/female_walk_front_variants_review.gif), [left](assets/characters/npcs/female_walk_left_variants_review.gif), [right](assets/characters/npcs/female_walk_right_variants_review.gif) and [back](assets/characters/npcs/female_walk_back_variants_review.gif).

## New terrain art

The first [Eldenmere grass/dirt pack](assets/terrain/eldenmere/grass_dirt/README.md) is approved at 24×24 pixels per tile. It contains four grass variations, a transparent 47-tile dirt blob atlas and three dirt interiors. The [character-scale review](assets/terrain/eldenmere/grass_dirt/review_scene.png), [complete blob atlas](assets/terrain/eldenmere/grass_dirt/blob_47_review.png) and [material samples](assets/terrain/eldenmere/grass_dirt/materials_review.png) show the approved fresh-green upland-village style. The scene is an art test rather than a canonical town map. Approved irrigation channels extend this foundation; terrace stone and environment props remain future work.

The first [animated stream-and-bank milestone](assets/terrain/eldenmere/stream/README.md) is approved following user review. Its [updated looping scene](assets/terrain/eldenmere/stream/review_scene.gif), [water-cycle close-up](assets/terrain/eldenmere/stream/water_cycle_review.gif) and [47-bank atlas](assets/terrain/eldenmere/stream/bank_47_review.png) use 24×24 tiles beside the approved ground and 24×36 characters. Six 200 ms phases animate local ripples while banks stay fixed; two surface variations share the same clock. This milestone establishes the water style before irrigation modules, terraces and working village props.

The [irrigation-channel milestone](assets/terrain/eldenmere/irrigation/README.md) is approved following user review. The [updated looping scene](assets/terrain/eldenmere/irrigation/review_scene.gif), [channel close-up](assets/terrain/eldenmere/irrigation/channels_closeup.gif) and [animated module board](assets/terrain/eldenmere/irrigation/modules_review.gif) show earth-lined 24×24 straights, bends, splits, stream inlets and trickling outlets. Directed currents use the approved water palette and six-frame timing; the channel walls stay fixed. The review extends the previous scene and preserves the existing approved assets.

The [stone terrace, steps and spillway milestone](assets/terrain/eldenmere/terraces/README.md) is a draft for visual review, following the approved design plan. Its [updated looping scene](assets/terrain/eldenmere/terraces/review_scene.gif), [enlarged terrace close-up](assets/terrain/eldenmere/terraces/terrace_closeup.gif) and [module board](assets/terrain/eldenmere/terraces/modules_review.gif) show warm fieldstone, a 24-pixel wall face, a four-tread 48×48 staircase and a six-phase spillway connecting the upper and lower irrigation. Stone stays fixed; falling highlights, impact flecks and ripples animate with the existing water clock. Characters on both levels establish scale.
