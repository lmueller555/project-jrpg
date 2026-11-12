# Sanctuary arrival: MQ03 emergency response

The arrival scene plays in the live Elden Vale Sanctuary reserve after the
acknowledged survivor report, Mira's rejoining and the actual road journey.
Its source is [`scene.json`](../assets/story/sanctuary_arrival/scene.json).
The Gallery entry uses the same scene in a disposable runtime. This scene does
not turn in MQ03, unlock MQ04, reveal the chasm or identify Vespermaw.

## Geography and cast

The party enters through the southern arch at `[444,642]`. The hall doorway is
at `[534,370]`; the three open cloister bays are at `[700,318]`, `[776,318]` and
`[852,318]`; the cave apron is `[1008,406]`. Camera orientation remains fixed,
with the cave east of the care stations and hall. There are no reverse angles
or camera rotation.

Two injured Crown workers shelter in the first two bays. A caretaker tends them,
a runner brings cloths from the hall, and a sentry watches the eastern
path. The existing survey ground remains evidence of the concealed operation;
its intact stone face is not newly excavated or blamed for the attack. The
grove, memorial lamps and ordinary Sanctuary architecture remain maintained.

The scene uses Caelan, Mira, Lucan, Aldric and the page. Serene, Tomas and the
driver remain in Eldenmere with the survivor. Nessa remains at the Sanctuary's
existing relief room; the arrival does not create a second attendant.

Full-player-foot stations and each successive actor goal were checked against
the actual reserve collision and pathfinder. Dialogue is player-paced. The
minimum phase times hold the physical action and shot; they do not dismiss
unread prose.

## Eight directed beats

| Beat | Composition and action | Dramatic purpose |
| --- | --- | --- |
| `arrival_contact` | Travel from the arch into the court. The camera discovers the occupied cloister as the group approaches. Mira tends an arm while Caelan speaks with the caretaker; Lucan checks the eastern sightline. | Establish an emergency already being managed, and follow through on Caelan's promise to Serene. |
| `accounting` | Lucan comes closer to ask who remains missing. The page opens the crew list beside Aldric while Mira continues practical care. | Establish one worker was pulled into the cave and has been heard answering since. The page's prior knowledge of the deployment remains unspecified. |
| `cave_reveal` | A silent 2.4-second hold on the crystal-lined cave approach, keeper rail and disturbed ground. | Let the viewer locate the threat. No interior, creature or chasm is shown. |
| `responsibility` | Return to a steady composition containing Aldric, the caretaker and wounded workers. The caretaker stands between Aldric and the people affected by his orders. | Aldric admits he acted without Serene's agreement, suspends the work and offers useful aid. Accepting his help does not settle the breach of trust. |
| `rescue_decision` | Mira finishes the dressing, withdraws her tools and stands beside Caelan. Lucan moves into a commanding position facing them. | Mira's engineering tools give her a practical rescue role; Caelan insists on following through. Lucan accepts their involvement while retaining his protective, somewhat overbearing manner. |
| `royal_handoff` | Hold the group while Lucan turns back toward Aldric, receives the order and turns toward the cave again. | Aldric explicitly releases his guard to accompany the rescue. Aldric and the page remain with the caretakers and crew list. |
| `visitor_rest` | Reframe toward the hall as the caretaker gestures and the runner returns toward its doorway. | Establish Nessa's visitor room: through the hall, then the north door with the bed plaque. The bed remains available during cave exploration. |
| `cave_approach` | Follow Caelan, Mira and Lucan along the eastward path. Aldric/page continue their work behind them. Lucan checks the opening; Mira watches loose stone; the caretaker unhooks the rope, lowers it and steps clear. Finish at the actual gameplay camera position. | Give the rescue a clear immediate aim and return control without a staging jump. |

The eight beats contain 38 authored dialogue lines. Workers retain injured
poses while Mira's dressing work, the page's reading and runner's supply work
provide restrained background activity. Important admissions and the rescue
decision receive steady compositions rather than reaction montages.

## Character follow-through

- **Caelan:** Reports that Serene is treating the survivor, asks where help is
  needed and commits to bringing the missing worker back.
- **Mira:** Helps a wounded person first, finishes the immediate dressing before
  moving on, and explains why engineering tools matter to the rescue.
- **Lucan:** Checks the approach, accounts for people and requests an exact last
  known location. He initially orders the younger pair to remain behind, then
  accepts their practical contribution. He does not repeat his earlier surprise
  about the secret deployment as a new discovery.
- **Aldric:** Owns the orders, admits the absence of agreement and stops the work.
  His concern is sincere; the Sanctuary's dispute with him remains unresolved.
- **Page:** Uses the crew list and helps account for survivors. The scene does
  not establish complicity in the secret deployment.
- **Caretakers:** Continue caring for the wounded, provide firsthand information,
  maintain the Sanctuary and explain the recovery room.

## Gameplay and continuity handoff

Lucan becomes a temporary third combat member with Caelan and Mira for the MQ03
Sanctuary outing. This is not his later permanent entrustment to the party.
Aldric and the page remain in the reserve. The player regains control on the
apron, with both the cave interaction and the path back to the hall available.
Entering the cave continues into the existing aether-resonance introduction.

Kindled Courage carries the arrival scene. The first actual cave entry ends
its MQ03 override for that journey; subsequent area transfers use normal music.
The caretaker's invitation is a continuing recovery option, not an automatic
heal or a new item requirement. Dialogue gives no medical countdown that would
make preparing or returning to rest contradict the rescue.

The report establishes a missing worker believed alive inside the cave. It
requires a later rescue payoff; arrival itself does not invent a rescue,
complete the boss, grant rewards or resolve MQ03. The characters do not yet know
that the bridge storm's aether surge opened the deeper rupture. That causal
connection remains author continuity until discovered in subsequent scenes.


## Character identity, movement and rope polish

Aldric's native navy coat and brown hair now match his existing portrait and
cinematic design, including his seated meal pose. His deterministic exporter is
`tools/build_regent_aldric.py`.

The Page uses the brown-haired, moss-coated design established in the larger
arrival cinematic and its dedicated `regent_page` portrait. His native 24×36
art includes four standing directions, eight-frame gaits, six-frame ledger
sequences and a matching meal pose. `tools/build_regent_page.py --check`
validates the exports and retained design recipe. The technical `regent_clerk`
identity remains compatible with earlier journeys.

The two injured workers retain distinct faces and workwear: the dark-haired
worker in reddish clothing speaks, while the brown-haired worker in olive rests
his leg. The grey-haired caretaker wears Sanctuary service colors. Their
portraits and native poses are registered by
`tools/build_sanctuary_arrival_art.py`; they do not reuse the survivor who remains
in Eldenmere.

`SanctuaryBlocking` consumes finite movement tracks from `scene.json`.
Authored lanes, departure delays and intermediate stations separate all ten
actors' full 24×12 ground probes. The page's work station lies outside the cave
approach. The runner makes one delivery and remains at work. The opening camera
tracks the arriving column before settling on the courtyard composition.

The barrier stands on the accessible apron at `[972,359]`, with stationary posts
and sixteen separately authored rope frames. The caretaker operates the right
fastening from `[1052,404]`, using a twelve-frame interaction with its own canvas
anchor. Hand and rope contacts share a 1.6-second timeline; a quiet sound marks
the release. The rope is guided down, released and settles on the ground while
the posts remain fixed. The caretaker then steps clear to `[1052,426]`.

`SanctuaryRope` adds reversible, local post/closed-rope footprints without
changing the cave façade's static boundary or the existing entrance interaction.
The closed rope's footprint releases at the same cue as the visible fastening.
The final positions, facings, Page reading hold and open rope reconstruct from
the acknowledged arrival checkpoint. An interrupted final beat rebuilds its
unacknowledged starting arrangement. Gallery restart restores the closed rope;
pause and focus loss freeze the interaction and sound.

The remaining dialogue reduction, medical acting, general care-supply
continuity and contextual post-scene conversations belong to the next polish
pass. This pass preserves the eight story beats and their quest consequences.
