# Sanctuary arrival: MQ03 emergency response

Character–object work follows the mandatory
[global interaction standard](OBJECT_INTERACTION_STANDARD.md) and its
[personal-prop visibility companion](PERSONAL_PROPS.md). Local coordinates,
contact timings, and captures below describe the current implementation.
Natural proportions and readable intent take priority over exact hand contact;
a small, deliberate transfer snap is acceptable.

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
| `accounting` | Lucan comes closer to ask who remains missing. The page opens the crew list beside Aldric; Mira remains beside the treated worker and her supplies. | Establish one worker was pulled into the cave and has been heard answering since. The page's prior knowledge of the deployment remains unspecified. |
| `cave_reveal` | A silent 2.4-second hold on the crystal-lined cave approach, keeper rail and disturbed ground. | Let the viewer locate the threat. No interior, creature or chasm is shown. |
| `responsibility` | Return to a steady composition containing Aldric, the caretaker and wounded workers. The caretaker stands between Aldric and the people affected by his orders. | Aldric admits he acted without Serene's agreement, suspends the work and offers useful aid. Accepting his help does not settle the breach of trust. |
| `rescue_decision` | Mira finishes the dressing, withdraws her tools and stands beside Caelan. Lucan moves into a commanding position facing them. | Mira's engineering tools give her a practical rescue role; Caelan insists on following through. Lucan accepts their involvement while retaining his protective, somewhat overbearing manner. |
| `royal_handoff` | Hold the group while Lucan turns back toward Aldric, receives the order and turns toward the cave again. The page lowers his open ledger and looks up to speak, then resumes reading. | Aldric explicitly releases his guard to accompany the rescue. Aldric and the page remain with the caretakers and crew list. |
| `visitor_rest` | Reframe toward the hall as the caretaker gives directions; the runner remains beside the delivered supplies. | Establish Nessa's visitor room: through the hall, then the north door with the bed plaque. The bed remains available during cave exploration. |
| `cave_approach` | Follow Caelan, Mira and Lucan along the eastward path. Aldric/page continue their work behind them. Lucan checks the opening; Mira watches loose stone; the caretaker unhooks the rope, lowers it and steps clear. Finish at the actual gameplay camera position. | Give the rescue a clear immediate aim and return control without a staging jump. |

The eight beats contain 28 authored dialogue lines. The treated worker presents
his arm only for care, then lowers it to a supported rest. Mira's dressing work,
the page's reading and runner's supply work provide restrained background
activity. Important admissions and the rescue decision receive steady
compositions rather than reaction montages.

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

Lucan becomes a temporary level-five third combat member with Caelan and Mira
for the MQ03 Sanctuary outing. He earns no combat EXP during this guest role
and uses Inspire, Bolster and Provoke without an interactable minigame. This is
not his later permanent entrustment to the party. He stays through early rest
trips and leaves only after Vespermaw is defeated and the party exits the cave;
Continue and re-entry preserve that departure.
Aldric and the page remain in the reserve. The player regains control on the
apron, with both the cave interaction and the path back to the hall available.
Entering the cave continues into the existing aether-resonance introduction.

Something is Wrong carries the arrival scene. The first actual cave entry ends
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
fastening from `[1052,394]`, facing left, using a sixteen-frame interaction with
its own canvas anchor. His feet are about 15 native pixels from the right post's
base at `[1037,392]`; the fastening is at `[1038,376]`. His shoulder, elbow and
wrist remain naturally proportioned. A small contact gap is permitted instead
of extending his arm to force exact hand/free-end coincidence.

The hand and rope share a 1.6-second timeline: approach/contact at 300 ms,
unhooking at 400 ms, guided slack until 800 ms, then free fall and settling. A
quiet sound marks unhooking. The left end stays attached and both posts remain
fixed. After releasing the rope, the caretaker withdraws his hand and steps
clear to `[1052,426]`.

`SanctuaryRope` adds reversible, local post/closed-rope footprints without
changing the cave façade's static boundary or the existing entrance interaction.
The closed rope's footprint releases at the same cue as the visible fastening.
The final positions, facings, Page reading hold and open rope reconstruct from
the acknowledged arrival checkpoint. An interrupted final beat rebuilds its
unacknowledged starting arrangement. Gallery restart restores the closed rope;
pause and focus loss freeze the interaction and sound.

In disposable quest playtests, each beat and the final party handoff advance
in memory without writing a journey. Disabled saving is intentional in this
mode and must not trigger the checkpoint retry prompt. Normal journeys still
require a successful save; actual write failures roll back the beat and party
handoff until the player retries successfully.

The performance pass below completes dialogue, care-supply continuity and
contextual replies while preserving these eight story checkpoints.


## Dialogue and performance pass

The eight checkpoint beats now contain 28 player-paced dialogue boxes. Stable
line IDs own one-shot care cues; pagination does not replay them. Mira checks
the existing dressing beside the worker before acknowledging her final care
instruction, retrieving her kit, and departing. Fast confirmations wait for
required short contact actions and never accumulate multiple advances.

### Interaction stations and native anchors

Native care, retrieval and linen placement artwork comes from
`tools/build_sanctuary_care_performance.py` (use `--check` for reproducibility).
The performance manifest registers character ground stations and each prop's
support anchor and contact point. All coordinates below are **native world
pixels**, before camera or display scaling:

| Character or object | Ground/support position | Staging |
| --- | --- | --- |
| Worker A | `[688,318]` | Presents his forearm toward Mira, then returns it to supported rest. |
| Mira | `[712,318]` | 24 px from the worker; turns toward each supply and uses authored bend/kneel poses. |
| Mira's kit | `[704,328]` | About 13 px from Mira's feet, within natural floor-object reach. |
| Clean linen beside Mira | `[724,324]` | About 13 px from Mira's feet; separate from the dressing retained on the arm. |
| Runner | `[800,350]` | Stops before lowering the bundle. |
| Delivered linen | `[790,358]` | About 13 px from the runner's feet; stays fixed after release. |

Prop support positions are not image top-left coordinates. Rendering subtracts
the prop's local support anchor to obtain its image origin; hand gaps use its
separate contact point. Enlarged action canvases preserve the character's
ground registration. Use the global standard's hand-contact ranges and visual
review; neither these station coordinates nor older exact-contact checks
justify stretched arms or sliding planted feet.

### Care, delivery and ledger lifecycles

Mira's sequence is **place → take cloth → treat → finish → retrieve**. She stops
and faces the kit destination before lowering it with a natural body bend. The
kit remains in her grip until its release cue, then becomes one fixed world
prop. She turns toward nearby linen, takes a cloth at its pickup cue, and turns
back toward the worker. During treatment, the dressing is secured on the arm;
Mira withdraws her hands while the worker returns his arm to supported rest.
She does not hold an exaggerated reach throughout later dialogue.

After her final care instruction, Mira faces the kit, grasps and lifts it, then
stows it and recovers before walking toward the rescue group. The remaining
clean linen stays beside the worker. Each transfer has one owner and one
representation; advancing dialogue cannot publish a placement or retrieval
before its physical cue. Her action facing takes priority over conversational
turns while she is manipulating an object.

The runner carries one consistently sized linen bundle along her finite route,
with directional carry art and body-appropriate occlusion. She stops, faces the
delivery spot, bends and lowers the bundle, then releases it to its registered
world support. The deposited bundle remains fixed as she recovers and settles;
there is no repeated supply loop or floating travel overlay.

The page remains at his left-facing reading station with the ledger registered
to his hands and torso. On his `royal_handoff` line, `read_attention` lowers the
still-open ledger and lifts his chin toward the listener; `read_resume` returns
him to reading after acknowledgement. Both are six-frame, 600 ms actions with
continuous start/end drawings. He continues reading after the scene; no physical
handover or new stowing action is implied. Any later turn or departure must use
appropriate directional artwork or finish and stow the ledger first.

Quiet contact sounds share pause, focus and cleanup behavior with the rope.

Deposited linen is a nonblocking world prop rendered at a fixed location during
and after the cinematic. Mira's personal kit disappears at retrieval before she
walks. Continue rebuilds props from the acknowledged beat. Emergency actors
have short optional replies; the gardener and cave observations select context
from the actual arrival/quest state, without inventing a renewed sighting or a
rescue resolution. Gallery instructions identify P as pause and Escape as exit.

### Personal props in this scene

The [global interaction standard](OBJECT_INTERACTION_STANDARD.md) and
[visibility policy](PERSONAL_PROPS.md) govern this scene. Mira's retrieved kit
is hidden before travel, while deposited linen remains at its world station.
Caelan's separate weapon overlay belongs to the authored MQ03 scabbard cue.
The documented rope and forearm grip coordinates are existing registrations;
they do not require future actions to force exact contact or extend limbs.

### Review scope

Check the live Gallery scene at native gameplay scale for approach, reach,
transfer, recovery and departure, including body proportions, contact gaps,
foot placement and foreground/actor occlusion. Focused checks protect single
ownership and cue timing across slow/rapid input, pause/focus changes, restart
and checkpoint restoration; completion alone does not establish visual quality.
Clean-water fetching and individual engineering-tool use remain dialogue
references. This interaction pass does not add those actions or a new medical
or inventory effect. Earlier review captures remain historical evidence rather
than certification of the revised performance.
