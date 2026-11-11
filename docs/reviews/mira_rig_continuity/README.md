# Mira: phase-three continuity review

Mira now wears her external engineering arm rig in exploration, workshop work
and the Ice Reaper cinematic. MQ01–MQ03 dialogue describes the brace, emitter
and tools. Her intact hand and arm remain part of the design.

The retired autonomous companion, its action catalog, scheduler, artwork and
builders have been removed. Compatibility is isolated in the journey migration;
recognized older saves retain their story, party, inventory and character data.
Current six-unit power allocation, direct techniques and combat balance are
unchanged from phase two.

## Review media

- [Four directions and walk poses](directions.png)
- [Workshop cycle](workshop.gif)
- [Cinematic equipment study](cinematic.gif)
- [Current live combat review](../mira_rig_combat/README.md)

These images use the production renderers in a disposable, nonpersistent
fixture. Workshop stills sample its eight-second cycle; cinematic stills seek
specific production timestamps. They are visual studies, not a claimed quest
playthrough. `evidence.json` records timestamps and source fingerprints.

## Reproduction and checks

Run `python tools/build_mira_rig_continuity.py` for registered exports and
`python tools/capture_mira_rig_continuity.py` for this review. Authored source
atlases and export registration live under
`assets/source/characters/mira/arm_rig/`.

Regression coverage includes rig rules and saves, old-loadout migration,
KO/barrier cleanup, guided Boar and cave battles, quest playtest starts,
MQ01–MQ03 dialogue, workshop timing, directional registration, cinematic cuff
emitter placement and deterministic art rebuilds. Historic review packs showing
the removed companion or replaced Mira equipment have been retired; current
combat evidence is linked above.

The broader pre-existing suite has failures in old spoils continuation/command
layout assertions and Caelan approval-document hashes. These reproduce on the
parent `main` revision (`7fa97c26`); phase three does not change those UI rules
or Caelan assets. The focused continuity, migration and combat checks above are
the verification for this cutover.
