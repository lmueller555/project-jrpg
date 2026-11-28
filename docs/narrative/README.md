# Narrative sources and ownership

Start here for story, character, world and revelation work. Read the
[Narrative Director guidance](../agents/NARRATIVE_DIRECTOR.md) for the writing
method, then follow the sources relevant to the assignment.

## Source owners

| Subject | Owning source |
| --- | --- |
| Aether conservation, Worldveins, natural and artificial imbalance, Veinholds, cannon and Ice Dome physics, and open foundational decisions | [Foundational Lore](saga/FOUNDATIONAL_LORE.md) |
| What characters and players may learn, reveal design and disclosure boundaries | [Revelation Plan](saga/REVELATION_PLAN.md) |
| Game I requirements, revised opening direction, later chronology and introduction windows | [Game I Story Bible](game_01/STORY_BIBLE.md) |
| Historical unapproved premises and act outlines | [Historical alternatives](archive/README.md); these do not override active canon |
| Approved Fire Veinhold opening sequence, retired requirements and implementation decisions | [Chapter 1](game_01/CHAPTER_01.md) and its linked quest scripts |
| Revised Fire attack, bridge chronology, local damage and recovery constraints | [Regional attack guide](game_01/REGIONAL_SURGES.md) |
| Individual characterization and voice | [Cast index](game_01/CHARACTERS.md) routes to [Caelan](game_01/characters/CAELAN.md), [Mira](game_01/characters/MIRA.md), [Iselin](game_01/characters/ISELIN.md), [Lucan](game_01/characters/LUCAN.md), [Rhea](game_01/characters/RHEA.md) and [Edran](game_01/characters/EDRAN.md); [template](game_01/characters/TEMPLATE.md) defines profile status |
| Supporting households and characters including Queen Althea, shared party relationships, lore exchanges and approved companion-art references | [Cast and supporting-household index](game_01/CHARACTERS.md) |
| Mira's established workshop-bot departure beat and open implementation | [Mira's departure section](game_01/characters/MIRA.md#planned-departure-beat) |
| Canonical world map, world geography, named kingdoms, standard adjective forms and cross-region connections | [World Atlas](world/WORLD_ATLAS.md) and its linked continent, polar and regional guides |
| Serene's spiritual tradition, Sanctuary guidance and remembrance practices | [Elden Vale Faith](world/ELDEN_VALE_FAITH.md) |
| Sanctuary custody background and former quarry-story context; revised cave purpose remains open | [Sanctuary Covenant](world/SANCTUARY_COVENANT.md) |
| Scene production references and placement limits | [New Fire Veinhold cinematic](scenes/FIRE_VEINHOLD_PROLOGUE.md), [retired opening cinematic](scenes/OPENING_CINEMATIC.md), [retired arrival](scenes/REGENT_ARRIVAL.md), and [independently retained Ice Reaper study](scenes/ICE_REAPER_PRE_BOSS.md) |
| Current-runtime ordinary household and mill scripts | [MQ01](game_01/CH01_MQ01.md) and [MQ02](game_01/CH01_MQ02.md) |
| Retired quest permalinks | [Former MQ03](game_01/CH01_MQ03.md) and [former MQ04](game_01/CH01_MQ04.md) |

Use the owner for a fact rather than maintaining another full copy in a related
guide. Brief context and a source link are appropriate. A regional guide can
explain why protected ground matters to its residents without reproducing the
quest's dialogue and saved completion sequence.

## Approved opening revision — 2026-11-26

[Chapter 1](game_01/CHAPTER_01.md) is the detailed owner of the replacement
opening: playable Fire Veinhold infiltration, Iselin's failed protection,
survivors' arrival, the misfired Fire attack and the party's return expedition.
The old opening cinematic is scrapped entirely as active narrative. The
Festival of Light and its preparation arc are removed. The old quarry-driven
opening spine and pre-opening lightning bridge cause are superseded.

The old cinematic, regent arrival, MQ03 and MQ04 have now been removed from
current gameplay, Gallery and Quest Playtests. New Game begins directly in the
bedroom; MQ01/MQ02 use ordinary household dialogue and retain their actual
flow, rewards and learning. The regional bridge now starts intact, with
layered phase art and a bounded west-bank road. Explicit damage/repair states
are retained, while the old `legacy_layout` scenery placeholder loads intact;
no attack or repair event is inferred. The new cinematic's
[production owner](scenes/FIRE_VEINHOLD_PROLOGUE.md) records the implemented
55-second Gallery presentation, including Bridge Ascent, and links its source,
native-frame, reproduction and runtime evidence. The playable
Fire Veinhold prologue, new arrival,
attack/invasion and repair quest remain future implementation. The
[overworld guide](../OVERWORLD.md) owns runtime details. Historical reviews
stay untouched; retired guides are small permalink notices rather than another
live opening script.

The replacement has explicit open decisions. A cave bypass, the two early
weapons being one battery, stolen intelligence, the precise return objective,
repair method and a named southern town are not approved through repetition.
Use Chapter 1's decision table before writing scenes that depend on them.
General faith, character foundations, southern world geography and the later
Ice Reaper chronology retain their existing owners.

## Current map authority

The [World Atlas's approved-map section](world/WORLD_ATLAS.md#approved-world-map)
owns the 2026-11-25 geography migration and links the canonical asset. Western
Merovar now extends far south; Elden Vale occupies its separate southern
watershed, while Adamanthra remains in the far north. Detailed geography stays
in the existing atlas, continent and regional owners rather than a second map
or country bible. Local playable orientation and approved companion home
regions retain their authority. Historical map captures are evidence of their
own versions, not competing current geography.

## Status and knowledge

- **Established / approved / canon:** Explicitly accepted facts or direction.
- **Proposed / working interpretation:** Material that has not been adopted.
- **Open:** A decision that remains unresolved.
- **Implemented:** Behavior verified in the current game, distinct from approved
  future direction.

Follow the labels within each source; a document can contain more than one
status. Moving or merging text does not change its approval status. An
illustrative scene does not become history, and a compelling proposal does not
become canon through repetition.

Author truth, character beliefs and player knowledge are separate. The
Revelation Plan governs disclosure even when an author-facing source states a
secret plainly. Report contradictions in the relevant scope rather than
silently selecting a convenient version.

## Runtime guides and historical evidence

[Story implementation](../STORY_IMPLEMENTATION.md) and the top-level scene,
quest, map and system guides describe runtime integration and production
constraints. They are not alternative owners of plot or cosmology. Technical
art and layout material, including the
[Eldenmere blockout](../world/eldenmere/blockout/README.md), retains its own
location outside this narrative collection.

Files under `docs/reviews/` retain captures, transcripts, approval records and
historical validation. They are evidence, not competing present-day canon.
Preserve their recorded content and status; update navigation links when a
source moves rather than rewriting a historical transcript to match new lore.

## Later story approvals

The approved names are **Adamanthra**, Iselin's northern Merovaran kingdom;
**Queen Althea**, its ruler and Iselin's elder sister; and **Carcovia**, the
industrious, shrewd kingdom on Serevin seeking expansion into Merovar through
aether-powered military force. The [atlas](world/WORLD_ATLAS.md#named-kingdoms)
owns geography, adjective forms and naming intentions; the
[cast index](game_01/CHARACTERS.md#queen-althea) owns Althea's brief entry.
Capital and dynasty names, Carcovia's ruler and exact political borders remain
open. Authorial naming associations do not establish literal disease or
in-world etymologies.

The 2026-11-24 Worldvein revision replaces the earlier cosmic catastrophe,
Ancients, Great Sacrifice, four-survivor plot and artificial atmospheric origin.
They are retired premises, not secrets awaiting revelation. The existing lore
owner now records elemental circulation, natural disasters, Veinholds (called
"clots" by some opponents), the enemy cannon ultimatum, and the dome's costs.
Iselin absorbs accumulating barrier aether during confinement, weakening the
dome; defeating her releases the excess and restores the Ice Worldvein.
These are approved future-story facts, not new runtime systems. Weapon supply,
the three-year military situation, exact absorption/release mechanics, Iselin's
fate and safe handling of the physical dome remain open in their owners.

The 2026-11-24 author-approved parallel journey, playable exile, conscious
ice-stasis transformation, planetary-core interval and Rhea's absence are
recorded in the [shared chronology](game_01/STORY_BIBLE.md#approved-later-progression-and-parallel-chronology)
and its linked character, lore and revelation owners. These are future story
direction, not implemented scenes. Unchosen causes, names and outcomes remain
open; suggestions made during discussion are not automatically canon.

## Consolidation record

The 2026-11-24 organization combines the former top-level foundational lore and
duplicate Saga Bible summary in `saga/FOUNDATIONAL_LORE.md`. Unique proposed
saga horizons and open questions remain labeled. Substantive world documents
now live under `world/`; technical blockout and title-art material remain under
`docs/world/eldenmere/`. This organization introduces no new story facts.

Game I structure now has one active Story Bible. The older Hollow Harvest and
Broken Covenant alternatives remain in `archive/` with their proposal statuses.
Individual companion foundations live in character sheets; shared relationships,
voice examples, art references and supporting household facts remain in the cast
index. The workshop-bot intention belongs to Mira's departure section, and the
Ice Reaper study belongs to its scene owner. These moves preserve approval and
knowledge boundaries and introduce no new story facts.

The four legacy MQ04 script installments formerly formed one implementation reference
with part anchors and their original local scene numbers. MQ04 and the old
opening/arrival runtime are now removed; their files retain only historical
permalink notices. Runtime guides retain technical ownership/save/presentation
contracts and refer to quest scripts for narrative. The separately recorded
later-story approvals above are additions after the structural migration.
