# Echo Chamber chasm review

The rear rupture is composed from the expanded limestone module pack, with
collision on the opening and unstable lip. Both side routes and a broad front
staging area remain intact. Eleven restrained aether strands rise from depth;
Reduced Motion holds the effect steady. The matching boss battlefield retains
clear actor slots in front of the opening.

Review media are produced by `python tools/capture_echo_chasm.py` using the
production world and combat renderers in a disposable, nonpersistent fixture.
These are visual studies, not a played quest or boss-victory claim.

- [Exploration](exploration.png)
- [Rising aether](exploration.gif)
- [Reduced Motion](reduced_motion.png)
- [Boss combat composition](combat.png)
- [Reduced Motion intro reveal](intro_reduced.png)
- [Terrain modules](modules.png)

The chasm has no descent link or rewards and remains after victory. Save
migration moves only positions newly covered by the opening, including matching
pending encounter coordinates; existing resources and progress are preserved.

Validation: **82 tests and 383 subtests passed**, including full-foot navigation,
blocked running, old checkpoint recovery, pending/awarded boss continuation,
effect pause/Reduced Motion, audio lifecycle and cave music. Module exports
rebuild byte-identically; map and battlefield reproducibility checks pass.
See [validation details](validation.json).
