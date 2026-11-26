# Retired opening cinematic — current-runtime reference

**Narrative status:** Scrapped entirely by the approved Fire Veinhold opening
revision, 2026-11-26. The [revised opening](../game_01/CHAPTER_01.md) owns the
replacement. This scene is not a future narrative requirement.

**Implementation status:** The old cinematic still runs in the current game.
Its removal from New Game, Gallery and any obsolete runtime references is a
subsequent implementation task. This documentation change does not remove code,
art, audio or saved-state behavior.

## Retired story contract

The late-journey Caelan/Mira flashforward, damaged wayside sanctuary, threatened
valley, lamp restoration, evacuation flare, anonymous bloody helmet and sword,
unidentified “he” and intended Act IV/V reprise are all retired with this
opening. The story owes no later recreation or explanation of those images.
Neither Tomas nor the new prologue soldier inherits the helmet's implied death.
The independently developed Ice Reaper confrontation remains in its own owner.

The production descriptions and original 30-line transcript below are retained
only as reference for the old implemented scene and its existing checks. Their
prior approval does not make them active canon or authorize reintroducing the
scene into the new opening. Historical [captures](../../reviews/opening_cinematic/README.md)
remain evidence of that version.

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
