# Opening cinematic — a light before the approach

New Game opens on a brief glimpse of Caelan and Mira much later in their
journey. They rest in a damaged wayside sanctuary overlooking an inhabited
mountain valley. A cup, a traveling lantern and a recollection of the mill
establish exhaustion and familiarity before the scene returns to Caelan's
ordinary sanctuary bedroom and Tomas's existing first line.

The 198.7-second sequence begins with “Later in the journey…” to identify the
flashforward explicitly. [Watch the captured opening](reviews/opening_cinematic/README.md).

## Story contract

The user approved this opening frame and its somber, cinematic presentation.
The current working narrative places its eventual reprise near the Act IV/V
boundary, before the final approach to the regional complex. That later
placement, the crisis's exact mechanics and the broader five-act outline remain
working story material. This change does not implement the late-game quests or
approve their unresolved outcomes.

Caelan and Mira reaching this moment is a deliberate limited disclosure. The
scene does not establish Tomas's fate, Eldenmere's ultimate condition, a death
or a specific bereavement. The lantern is ordinary traveling equipment, not
Liam's tower lantern or somebody's memorial keepsake. The sanctuary is a
wayside resting place, not a revelation of the ancient sacrificial temple.
Aldric's responsibility, the regional mechanism and all saga-level mysteries
remain concealed. Caelan's familiar faith is not declared false.

The expanded exchange establishes an entrance beyond the ridge, a road
threatened by another local surge, evacuation carts and the pair’s help with
the first group. These are approved facts of the framing scene. They do not
settle the cause of the crisis, its mechanism or the wider later-act plot.

The later narrative should return to this scene and continue beyond the final
line, giving its quiet exchange a context the player has earned. That reprise
remains future work.

## Presentation

The scene uses the detailed battle-art style with separate scenery layers and
new resting/conversational actor poses. Camera shots establish the valley,
move to the lantern-lit pair, hold their conversation and return attention to
the approach ahead. Local animation gives the light, fabric and atmosphere
motion without continuously moving the conversation's frame.

Dialogue advances automatically. Text uses the shared display-resolution
renderer and respects the readability setting. Camera shots and captions belong
to the cinematic, while the ordinary world, morning action sequence and quest
state remain suspended.

Ordinary gaps between lines are one second, reduced from the original two.
The two four-second pauses allow the sitting/drinking action and the final
shared hesitation. Short replies have shorter display holds; longer lines
retain time to read. The expanded sequence runs for about three minutes and
nineteen seconds. Caelan lifts, sips and lowers the cup during a quiet beat,
with the same forward/downward head bearing and planted seated anchors.

## Approved dialogue

- **Mira:** “Here. While it’s warm.”
- **Caelan:** “Thank you.”
- **Mira:** “Your hands are still shaking.”
- **Caelan:** “They’ll stop.”
- **Mira:** “So will mine, if I give them a minute.”
- **Caelan:** “How far to the entrance?”
- **Mira:** “Beyond the ridge. There’s some climbing yet.”
- **Caelan:** “I can manage.”
- **Mira:** “I know. I’m asking you to rest.”
- **Caelan:** “*looks across the valley* There are still people in those houses.”
- **Mira:** “The carts are going back for another group.”
- **Caelan:** “And when we leave here, we’re going the other way.”
- **Mira:** “Another surge could take that road. We need to reach the source.”
- **Caelan:** “I wish we could tell them more than ‘we’ll do what we can.’”
- **Mira:** “We got the first carts through. They saw that.”
- **Caelan:** “I was thinking about the mill.”
- **Mira:** “Halden’s?”
- **Caelan:** “I cleared that little recess and felt as if I’d done something remarkable.”
- **Mira:** “You cleared the catch so I could work on it. We needed that.”
- **Caelan:** “*a faint smile* You told me that then, too.”
- **Mira:** “I meant it then, too.”
- **Caelan:** “You didn’t seem nervous.”
- **Mira:** “I was. It helped having a problem I could understand.”
- **Caelan:** “A broken catch. A branch in the water.”
- **Mira:** “And two of us to deal with it.”
- **Caelan:** “I wish it were that simple again.”
- **Mira:** “So do I.”
- **Caelan:** “But we’re going in.”
- **Mira:** “When you’re ready.”
- **Caelan:** “Give me a moment.”

## Music and controls

**Dare to Dream Leitmotif** is the exact user-supplied composition from
`assets/music/Dare to Dream Leitmotif.m4a`, exported as a runtime OGG and played
with repeat enabled throughout the scene. Music volume uses the existing
setting. Finishing or skipping hands back to **Eldenmere Theme** for the
bedroom morning.

- **Esc:** pause or resume the cinematic and its music without restarting them.
- **Skip:** a small bottom-right button ends the cinematic, including while
  paused, and starts the ordinary bedroom opening once.
- Window focus loss freezes presentation and music; returning focus preserves
  any explicit pause.
- Fullscreen and resizing remain available. Reduced Motion uses static shots.

## Journey boundaries

Every New Game starts the cinematic. Continue resumes the saved journey
directly. The flashforward grants no items, attributes, quests or future plot
flags. Starting or quitting the cinematic does not overwrite a previous
journey; the ordinary new-game checkpoint is established on entering the
bedroom. An interrupted cinematic is not serialized as playable future state.

`Game(start_on_title=False)` remains the direct world harness. Focused tools
and tests may use the explicit `show_cinematic=False` argument to
`begin_journey` when their subject is the existing morning or another quest.
The production title path uses the cinematic by default.
