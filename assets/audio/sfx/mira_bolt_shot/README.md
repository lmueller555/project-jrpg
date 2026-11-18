# Mira Bolt Shot contact

`bolt_impact.wav` is a 96 ms, 44.1 kHz mono PCM dry impact cue. Its damped
low body and seeded transient are synthesized from scratch by `build.py`;
there are no imported recordings. Rebuild with
`python assets/audio/sfx/mira_bolt_shot/build.py` from the repository root.

The battle scene requests this cue on the unguarded Bolt Shot impact event,
not on release. It uses the existing Effects setting and action-audio channel
cleanup. Guard contact keeps the existing cue.
