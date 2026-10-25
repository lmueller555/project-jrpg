# Tomas and Caelan — ambient opening exchange

**Status:** APPROVED for the first proximity conversation with Tomas in the
playable town (`tomas_greeting`). This is their conversation about his wheel,
separate from the wake-up and breakfast scenes in [the opening quest](CH01_MQ01.md).

Caelan is **18** and Tomas is **14**; see [approved character facts](CHARACTERS.md).
Tomas asks his brother for help with a specific difficulty, describes what he
can observe, and wants to solve it himself before asking Mira. Caelan takes
his interest seriously. Their familiar, plainspoken exchange uses workshop
words Tomas knows without narrating his routine or making chores the focus.

- **Tomas:** "Caelan, can you look at this?"
- **Caelan:** "What's wrong?"
- **Tomas:** "It turns most of the way, then it sticks. I can't see what's catching."
- **Caelan:** "Is the pin bent?"
- **Tomas:** "I thought so, but it looks straight."
- **Caelan:** "Have you shown Mira?"
- **Tomas:** "Not yet. I wanted to get it working myself."
- **Caelan:** "You can still ask her."
- **Tomas:** "I know. I will if I can't find it."

The game advances these lines through the existing click-to-advance portrait
dialogue. Completing the exchange sets `tomas_greeted` for the current session;
subsequent conversations use the existing `tomas_repeat` exchange. This
conversation does not start a quest or change Tomas's schedule.

Runtime text: `assets/dialogue/eldenmere.json`. The matching source text in
`tools/build_tomas_routines.py` preserves this approved exchange when rebuilding
the routine pack.
