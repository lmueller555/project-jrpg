# Opening cinematic — a light before the approach

New Game opens on a brief glimpse of Caelan and Mira much later in their
journey. They rest in a damaged wayside sanctuary overlooking an inhabited
mountain valley. A cup, a traveling lantern and a recollection of the mill
establish exhaustion and familiarity before the scene returns to Caelan's
ordinary sanctuary bedroom and Tomas's existing first line.

The 130-second sequence begins with “Later in the journey…” to identify the
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
