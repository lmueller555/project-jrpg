# Liam’s lantern quest — PR1

`CH01_MQ04`, **A Light of His Own**, follows completion of The Regent’s Road. This is the first of four implementation PRs for one continuous quest. It covers the school preparation session and Mira’s workshop, ending with an unlit tower-shaped frame. The full quest’s village encounters, break, sanctuary discussion, personal purpose and return to Liam’s mother follow in later segments.

## Playing the opening segment

After Aldric’s visit and Caelan’s final conversation with Serene, speak with Tomas in the sanctuary courtyard. His invitation continues MQ03’s existing call about the lanterns. Serene has her promised response to write; the brothers go to the school’s special preparation session.

Meet Liam’s mother and the six children, inspect Liam’s tower drawing, then finish the exchange in which his mother agrees to the outing. Accompany Liam and Tomas to Mira. Give Liam space to present his own design, test the shape, help with the corners and try the handle. Finish the reaction scene after the balance test.

The final frame stays at Mira’s table beside Liam’s drawing. It is unlit and still needs its finishing work. MQ04 remains **active** at `frame_ready`; PR1 does not complete it or unlock a festival placeholder. The journal describes this achieved milestone without directing the player toward an unimplemented interaction.

## Character and narrative boundaries

Liam is eight; Caelan is eighteen and Tomas fourteen. The brothers already understand the annual festival. Liam remembers previous celebrations, but this year asked to make and carry a lantern of his own. This is a personal first, not an established coming-of-age rule shared by every village child.

Liam’s mother is Eldenmere’s teacher, with her personal name still unassigned. She hosts the preparation session and explicitly agrees to the planned workshop outing. The same mother, Liam and five other children are used; their family identities and homes remain intact. Special quest attendance does not establish a general school timetable.

The tower design develops Liam’s existing love of building blocks. Mira takes the drawing seriously and helps him retain its defining shape. Tomas provides useful suggestions; Caelan gives practical help while respecting Liam’s wish to do some work himself. Liam can be excited, worried and proud without becoming an adult exposition voice. Occasional short parenthetical delivery cues carry emotion in the text.

There is no magical task in this segment. Caelan’s useful small success at the mill and failed forceful attempt at the Venn channel remain unchanged. Elira already has her retrieved memorial lantern; the later remembrance scene must build on that fact. Liam’s lantern purpose stays open here. The proposed lantern custom for someone without a person to carry one remains later design work.

## Dialogue and presentation

`assets/story/lantern/scene.json` contains nine main scenes: `invitation`, `classroom`, `design`, `permission`, `workshop`, `test_shape`, `assemble`, `lift` and `frame_ready`. `walk_chat` is optional. Short repeat replies are selected by committed progress; later craft facts must not appear before the player has reached them.

The complete speaker-attributed transcript is [CH01_MQ04](narrative/game_01/CH01_MQ04.md). All nine main exchanges are player-paced. Canceling or leaving one cannot commit unread consent, construction or success.

The drawing, material pieces, partial frame and finished frame make the work visible. One lantern state follows the work; a held and resting copy must not appear simultaneously. Craft poses preserve the approved idle bodies and believable limb lengths, with contact points registered to the materials. The frame is tested for balance without fire.

## Progress and save continuity

The quest definition establishes the full objective sequence from PR1, so later segments can extend the same active quest without migrating an already completed short placeholder. MQ03 completion makes it available; reading the invitation accepts it. Finishing this segment commits `frame_ready` while keeping later objectives outstanding.

`lantern_quest` stores versioned committed story progress. Dialogue cursors, partial animation clocks and path caches are transient. Restore reconstructs the appropriate actors, props and safe scene checkpoint. A newly gated MQ04 may be absent from older saves; completed MQ03 saves gain access without replaying the regent’s visit or its announcements. An active MQ04 requires matching valid story facts. New Game releases quest ownership and restores the ordinary opening routines.

The controller takes over Tomas only after MQ03 has released his staging, and coordinates Mira’s existing post-mill behavior. Liam’s block-building or shared Daisy routine must settle safely before the quest borrows him; the same actor’s location tracking stays accurate through doors. The mother and other children are borrowed from their existing home actors, not duplicated as classroom residents.

## Validation and review

Verify the complete segment using normal interactions, collision-aware movement and real door transfers. Cover cancellation and reload at each committed milestone; repeated interactions; active Liam/Daisy and block activity at handoff; actor identity across rooms; clear classroom, threshold and workshop approaches; no premature objective credit; and a clean New Game reset. Earlier quest outcomes, including the working mill and released Venn cart, must remain intact.

Review captures should show the actual game’s classroom, outing, workshop and visible frame, with readable dialogue stills. The complete game suite is required because character ownership, story handoffs and saves cross existing systems. Recorded test and capture results belong with the review artifacts, not as unverified claims in this guide.

## Chapter continuity

MQ04 happens on the preparation day and MQ05 on the next day. The broader [chapter structure](narrative/game_01/CHAPTER_01.md) now contains five main quests. The festival’s detailed activities and inciting event remain later work. The authorization letter remains the planned post-festival escalation, while the excavation catastrophe belongs to Chapter 3. In-world religious belief must remain distinct from concealed cosmic history.
