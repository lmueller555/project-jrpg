# Eldenmere interface

The interface uses deep forest green, warm ivory, muted brass and a small lantern
selection mark. Parchment surfaces distinguish the quest ledger and town map.
Frames, spacing and button feedback share the same renderer in `ui_style.py`.

## Readable text and crisp art

The world remains a 480×320 image with integer-scaled 24×24 terrain and 24×36
character frames. Interface text is drawn separately at the actual output
resolution with antialiasing. Enlarging the world never enlarges a small bitmap
of its lettering.

Gallery playback reserves a separate toolbar above its complete 480×320 scene.
This preview viewport uses nearest-neighbor fitting when an integer scale cannot
fill the available area; text is still rasterized at the output resolution.
The toolbar never covers dialogue, actors or the production Skip button.

Atkinson Hyperlegible Regular and Bold are bundled with the game. Their distinct
letter shapes and punctuation are used for dialogue, objectives, menus and the
journal; the approved serif game logo remains on the title screen. Font origin
and redistribution terms are recorded in `assets/ui/fonts/README.md` and the
adjacent license file.

Settings offers 100%, 125% and 150% text size. Text is remeasured when readability
or display size changes; layouts wrap, scroll or paginate instead of shrinking
the text to fit. Reduced interface motion and objective-tracker visibility are
saved alongside independent music and effects levels in `saves/settings.json`.
Existing audio-only settings retain their levels and receive the default UI
preferences. Journey saves remain separate.

## During exploration

Location plaques appear briefly on entering an area, while nearby interaction
prompts appear only when relevant. The permanent full-controls strip has been
removed. Controls remain available from the pause interface. The current
objective can be hidden without altering quest progress.

The exploration Menu button has been removed globally. Escape opens pause.
During regional overworld exploration, a compact illustrated minimap occupies
the bottom-right corner and opens the full atlas when clicked. It yields to
dialogue and modal screens; town and interior exploration have no replacement
corner button. HUD prompts account for the minimap's occupied area.

Dialogue remains part of the running world. Portrait bubbles follow the current
speaker, protect participants' faces and keep their response buttons inside the
viewport. Clicks advance prose; explicit response buttons handle quest choices.
Walking away closes unfinished dialogue without accepting an offer or completing
a report. Camera, world animation and other NPC routines continue normally.

## Menus and navigation

The title keeps its approved animated scene and bottom-center menu. Pause,
settings, buttons and selections use the shared green-and-brass treatment.
Gallery uses the same treatment with lazy-loaded scene thumbnails, wrapped names
and descriptions, a visible scrollbar, and retained selection on replay return.
Volume controls display percentages and accept mouse adjustment and keyboard
left/right or plus/minus. Readability settings apply to both title and gameplay.
At larger text sizes, settings can scroll; wheel navigation and keyboard
selection keep the selected entry visible. The controls reference is available
inside Settings on both the title screen and pause menu.

The journal presents quests separately from the selected quest's details and
objectives. The town map preserves Eldenmere's geography with simplified cartography,
selectable landmarks and a dedicated player legend. Both have visible close
controls in addition to their existing keyboard shortcuts.

The [regional atlas](REGIONAL_MAP.md) uses illustrated, geographically registered
terrain with live routes, markers and labels. A compact header and contextual
place card give the map most of the available space. Important names, passage
states and the player marker remain readable at different zoom and text sizes.

Navigation, confirmation and back sounds are quiet and follow the effects
volume. UI animation does not delay input, and reduced-motion mode preserves
immediate interaction.

## Scripted millrace dialogue

MQ02's arrival cutscene keeps the full world viewport while temporarily owning
actor movement and camera shots. The boar shot uses a fixed bottom portrait
panel; the returning party shot uses a top panel to keep both characters visible
near the map edge. Neither panel draws a speech tail toward an offscreen actor.
Pagination, text scaling and response input use the existing dialogue system.
Normal conversations retain their live speaker-anchored bubbles.

## New Game cinematic

The opening cinematic uses the battle scenes' detailed visual style with layered
scenery, separate conversational character poses and authored camera shots.
Dialogue is timed automatically and rendered at display resolution using the
shared text-size preference. A compact Skip button stays in the bottom-right
corner, including while paused. Escape toggles a dedicated cinematic pause;
it freezes camera, actors, ambient movement, captions and the looping leitmotif.
Focus loss also freezes the scene, without clearing a manual pause on return.
Reduced Motion uses static shot changes. Finishing or skipping leads into the
ordinary bedroom opening; Continue never inserts this flashforward into an
existing journey. See [the cinematic guide](OPENING_CINEMATIC.md).

## Aldric's arrival

The [post-mill arrival](REGENT_ARRIVAL.md) uses detailed cinematic scenery and
separate animated actors, with the existing portrait dialogue frame and
display-resolution text. Its dialogue advances at the player's pace. Escape
pauses/resumes, focus loss suspends playback, and a small Skip control remains
available. Reduced Motion removes continuous camera travel. Exploration and
its HUD stay suspended until the scene returns control at the mill. The visit
continues through ordinary, cancelable MQ03 dialogue afterward.
