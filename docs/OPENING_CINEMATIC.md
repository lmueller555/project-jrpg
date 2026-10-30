# Opening cinematic — a light before the approach

New Game opens on a brief glimpse of Caelan and Mira much later in their
journey. They rest in a damaged wayside sanctuary overlooking an inhabited
mountain valley. A cup, a traveling lantern and a recollection of the mill
establish exhaustion and familiarity before the scene returns to Caelan's
ordinary sanctuary bedroom and Tomas's existing first line.

The 252.57-second sequence begins with “Later in the journey…” to identify the
flashforward explicitly. [Watch the captured opening](reviews/opening_cinematic/README.md).

## Story contract

The user approved this opening frame and its somber, cinematic presentation.
The current working narrative places its eventual reprise near the Act IV/V
boundary, before the final approach to the regional complex. That later
placement, the crisis's exact mechanics and the broader five-act outline remain
working story material. This change does not implement the late-game quests or
approve their unresolved outcomes.

Caelan and Mira reaching this moment is a deliberate limited disclosure. The
author's revised ending now hints that someone has died: an anonymous bloody
metal helmet rests on a sword embedded in stone. It identifies neither the
helmet's owner nor whose death it suggests, and it does not settle Tomas's fate
or Eldenmere's ultimate condition. The reference to “he” in Mira's encouragement
remains the author's exact wording and leaves its context unresolved for the
player. The lantern is ordinary traveling equipment, not Liam's tower lantern
or an identified memorial keepsake. The wayside sanctuary does not reveal the
ancient sacrificial temple. Aldric's responsibility, the regional mechanism and
all saga-level mysteries remain concealed.

The author's exchange establishes an entrance beyond the ridge, a threatened
valley and a caravan returning for another group. Their reassurance, the lamp
repair and the blue signal connect this pause to the evacuation. These framing
facts do not settle the cause of the crisis or the wider later-act plot.

The later narrative should return to this scene and continue beyond the final
line, giving its quiet exchange a context the player has earned. That reprise
remains future work.

## Presentation

The scene uses the detailed battle-art style with separate scenery layers and
new resting/conversational actor poses. Camera shots establish the valley,
move to the lantern-lit pair, hold their conversation and return attention to
the approach ahead. Local animation gives the light, fabric and atmosphere
motion without continuously moving the conversation's frame.

Dialogue advances automatically through the same portrait dialogue panel used
in ordinary gameplay: the speaker portrait sits on the left beside the shared
border, speaker label, fonts and text spacing. Longer passages advance through
readable pages within their authored dialogue hold, without a click-to-continue
prompt. The shared display-resolution renderer respects the readability setting.
The cinematic owns dialogue timing and shot placement while the ordinary world,
morning action sequence and quest state remain suspended.

Ordinary gaps between lines remain about one second. The author's latest
30-line dialogue is preserved verbatim; longer lines receive enough time to
read. Visible cup placement, hand contact, repair and camera work own their
action beats. The sequence runs for about four minutes and thirteen seconds.
Caelan's corrected forward/downward drinking motion is retained.

## Authored actions and camera sequence

1. Caelan sets the cup on the bench, freeing both hands. Mira reaches for and
   holds both his hands before “Your hands stopped shaking. Mine too...I'm
   ready.” Contact continues throughout the line, then she releases him.
2. On Caelan's lamp request, Mira rises, walks around the bench on the clear
   foreground floor and kneels to the lamp's left. Her wrench work accompanies
   two visible partial restoration stages. This is mechanical repair.
3. Caelan stands and prepares a large blue signal. “This should help too” leads
   into its launch. The camera follows it upward into the extended sky, holds
   its firework burst and the small glimmering light it leaves behind, then
   pans down. The light persists in world space after leaving the shot.
4. Full restoration and “Ok there! Don't break on me now.” are gated by the
   completed downward pan. The lamp remains partial until the camera has
   returned, and becomes fully restored as Mira delivers that line.
5. Following the final exchange, both walk left at 48 pixels per second, a 20%
   increase in departure movement speed. Their existing walk animation cadence
   remains 180 ms per frame. The same paths now take about 12.92 seconds, and
   the smoothly eased camera follows for about 5.83 seconds, revealing the
   nearer sword and helmet as the actors pass behind them. At center view the
   camera stops while both continue offscreen.
6. Half a second after both are gone, the camera begins the existing ten-second
   helmet zoom, with the fade starting 1.5 seconds into it. The ordinary bedroom
   opening follows, with Tomas's original first line. The sword is hidden in the
   earlier valley shots to preserve its reveal.

Scene events, actor paths and camera shots are data in `scene.json`. Lamp stages
and the completion line have a runtime camera-return gate, rather than relying
only on caption ordering. Pause/focus loss freeze the same visual clock for
paths, actor loops, lamp state, flare particles, glimmer and zoom. Reduced Motion
uses static compositions and a restrained signal/fade. Skip remains available.

The flare depicts Caelan later in the journey. It does not change his starting
attributes, grant a combat ability or alter the modest early-quest magicks.

## Approved dialogue

- **Mira:** “Here. While it’s warm.”
- **Caelan:** “Thanks, Mira”
- **Mira:** “Your hands are still shaking. Mine too.”
- **Caelan:** “It'll be ok, they'll stop once we get moving.”
- **Mira:** “I hope you're right.”
- **Caelan:** “How far to the entrance?”
- **Mira:** “Beyond the ridge. There’s some climbing yet.”
- **Caelan:** “I can manage.”
- **Mira:** “I know. But you need to rest a bit first.”
- **Caelan:** “You know, there are still people in those houses.”
- **Mira:** “Yeah...but the caravan is going back for another group. They will make it out...I hope.”
- **Caelan:** “And when we leave here, we’re going the other way. It feels like we're turning our back on them.”
- **Mira:** “Maybe...but another surge like that could wipe out the whole valley. We need to reach the source so we can put an end to this.”
- **Caelan:** “I'm scared, Mira. We've come so far, but we still have so far left to go.”
- **Mira:** “It's ok, Caelan, I'm scared too. But I believe in you!”
- **Caelan:** “Mira...I was thinking about the mill.”
- **Mira:** “Halden’s?”
- **Caelan:** “Do you remember when I barely managed to clear that little recess? Would you ever have guessed we'd look back on that as the least of our troubles?”
- **Mira:** “*laughs* Ha...yeah that seems like a lifetime ago now. But, Caelan?”
- **Caelan:** “What?”
- **Mira:** “I know what else you're thinking about. I want you to know he's just as proud of you as I am.”
- **Caelan:** “...thanks. I'm feeling better...lighter.”
- **Mira:** “Your hands stopped shaking. Mine too...I'm ready.”
- **Caelan:** “This lamp...we'll leave it here. Mira, think you can you work your magic with it?”
- **Mira:** “Leave it to me! This beacon will guide the evacuation to safety.”
- **Caelan:** “This should help too.”
- **Mira:** “Ok there! Don't break on me now.”
- **Caelan:** “Huh? Me? Or the lamp?”
- **Mira:** “*smiles* Let's go.”
- **Caelan:** “Indeed.”

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
