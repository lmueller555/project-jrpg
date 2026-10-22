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

All three male NPC palettes have approved front, left, right and back stationary idles at 24×36. The [directional comparison](assets/characters/npcs/male_idle_directions_review.png) shows variants as rows and front, left, right, back as columns. All twelve directional idle frames are approved. Walking cycles are the next planned assets.
