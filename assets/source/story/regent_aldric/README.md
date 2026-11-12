# Aldric: canonical native identity

The approved Aldric portrait and larger arrival-cinematic body drawings establish
his brown hair, navy travelling coat, ivory collar, brass edging and leather
boots. Ordinary MQ03 artwork now uses that same identity instead of a gray-haired
villager whose material palette had changed underneath the old recolor recipe.

`tools/build_regent_aldric.py` exports the canonical head, coat and boots with
separate native registrations. Eight articulated gait phases share the normal
24×36 canvas, draw anchor `[12,30]` and foot anchor `[12,34]`. The left-facing
seated meal export retains his coat and face at the same registration.

Run `python tools/build_regent_aldric.py` to rebuild, or append `--check` to verify
the exports without modifying files. Every canonical input is hash-checked
against `recipe.json`; the regent builder preserves approved exports and delegates
new Aldric construction to this recipe.
