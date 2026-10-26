# The Regent's Road in game

[Complete quest overview](quest.gif) · [Cart release close-up](cart_release.gif).

The production game follows Caelan welcoming Aldric's party, accompanying the
visitors through the village and helping receive them at the sanctuary. Aldric
handles the road crew's expired cart hire; his clerk checks the terms. Caelan
contributes only his firsthand knowledge that Halden's mill is working again.
There is no player receipt inspection or adjudication objective.

The welcome and quiet covenant discussion keep the approved emotional dialogue
cues. Serene offers to pursue records and a joint review; the disagreement stays
unresolved, and this quest does not authorize excavation. Caelan's final exchange
with her is required before MQ03 completes. The mill remains restored.

## Capture method

Run `python tools/capture_regent_quest.py` with Pygame and Pillow installed. The
capture seeds only completed MQ01/MQ02 prerequisite facts and the starting
station. MQ03 advances through the real game's walking, public interactions,
dialogue callbacks and scene-controller clocks. It never assigns an MQ03 stage
or completes its objectives directly.

The compact 320-pixel-wide overview retains each main dialogue page and compresses
travel samples. Full-resolution UI stills accompany it, and the complete dialogue
script is in [CH01_MQ03.md](../../narrative/game_01/CH01_MQ03.md).
Review captions are outside the rendered game image. The separate cart clip
uses the same world renderer with a camera following the real Mr. Venn actor
and released cart. All exported GIF frames and cumulative durations are checked
against the indexed source images after decoding. The capture also checks that
all six main conversations appear exactly once with every dialogue page. A brief
clerk travel reminder can appear before the dispute is settled; its stage is
checked, and out-of-sequence visit reminders are rejected. The completed delivery
and parked cart are also checked, including clear access to Halden.

The PNG stills show the actual display-resolution game UI: preparation,
arrival, the dispute and ruling, the welcome, the covenant disagreement and
the personal aftermath.
