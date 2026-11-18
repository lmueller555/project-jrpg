# Repository instructions

Before creating or changing character/NPC sprites, animation, or corresponding
asset builders and tests, read the
[global sprite and animation standard](docs/SPRITE_ANIMATION_STANDARD.md).
It is the single authoring reference for design, directional anatomy, gait,
registration, export and review. Older recipes and review notes retain local
implementation facts and history, not competing construction rules.

For object manipulation, scene staging and prop rendering, also read
[the character–object interaction standard](docs/OBJECT_INTERACTION_STANDARD.md)
and [personal-prop visibility](docs/PERSONAL_PROPS.md).

Apply the standard to the work in scope:

- Approach and face the object; perform a recognizable, naturally proportioned
  action; then snap/transfer the object at its authored cue.
- Reasonably close hands are sufficient. Do not stretch anatomy or move planted
  feet to satisfy exact-contact coordinates or older tests.
- Preserve one object owner/location, camera-appropriate occlusion, and coherent
  cleanup/restoration. Personal props disappear after use; deposited props stay
  at their world destination.
- Check actual scene frames for anatomy, intent, depth, and facing, alongside
  focused tests for transfers and lifecycle state. Summarize the validation in
  the PR; do not claim visual compliance solely from passing completion tests.

The global standards supersede conflicting older scene notes, recipes, tests,
and historical review prescriptions. Retain historical evidence and local
implementation facts. Record other inconsistent existing interactions for a
scoped follow-up rather than silently expanding unrelated work.
