# MQ01 report and mill handoff

The player can now finish the three household visits, report to Serene and hear
Halden's approved mill-failure exchange. MQ01 completes after the final line;
MQ02 becomes available with **Find Mira at her workshop**. Mira's quest conversation
and the subsequent adventure are the next implementation milestone.

[In-game sequence](conclusion.gif) · [Report](report.png) ·
[Halden's arrival](arrival.png) · [Mira objective](mira_objective.png).

These are captures from the running Pygame game. The capture fixture seeds the
three completed household objectives and places Serene in the hall to begin the
review at the report. The report, Halden's real doorway entrance, dialogue,
notifications and tracker then run through the production game loop. It does not
claim to show a complete New Game playthrough.

Reproduce with `python tools/capture_opening_conclusion.py` (Pygame and Pillow).
The GIF retains the decoded palette-mapped frames, checked during export.

## Testing in game

Finish Halden, Elira and Venn, then approach Serene where she is working. Finish
the report and follow her to the hall if necessary. Halden enters through the
sanctuary door; approach Serene to hear the exchange. Read the final line to
receive completion feedback and the Mira objective. Exploration remains free.

Continue an older journey that already completed the report to receive just the
missing mill arrival. Saving/reloading unfinished arrival dialogue leaves the
exchange available without replaying completed reports or duplicating Halden.
New Game resets the conclusion and the mill's animation.

Tests: `python -m unittest discover -s tests -p test_opening_conclusion.py -v`.
