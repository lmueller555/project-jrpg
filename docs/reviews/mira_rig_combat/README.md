# Mira's live arm-rig combat review

These captures use the **ordinary combat scene and actual phase-two commands**.
They are separate from the title Gallery's phase-one art sandbox. The rig is
worn over Mira's intact arm, and the six-unit console controls real skill access.

## Layouts and routing

- [Two active characters, normal text](combat_2_party_text_100.png)
- [Two active characters, 150% text](combat_2_party_text_150.png)
- [Three active characters, normal text](combat_3_party_text_100.png)
- [Three active characters, 150% text](combat_3_party_text_150.png)
- [Protection 3 / Support 3](support_allocation.png)
- [Weapons 3 / Protection 1 / Support 2](offense_allocation.png)

## Executed skills

| Skill | Impact | Completed action |
| --- | --- | --- |
| Bulwark | [37-point barrier appears](bulwark_impact.png) | [Barrier retained after creating turn](bulwark_after.png) |
| Repair Pulse | [Caelan gains 41 HP](repair_pulse_impact.png) | [Mira has spent 4 MP; barrier has one turn left](repair_pulse_after.png) |
| Charged Bolt | [Physical impact](charged_bolt_impact.png) | [MP and enemy HP after the action](charged_bolt_after.png) |
| Arc Discharge | [Electric impact](arc_discharge_impact.png) | [MP and enemy HP after the action](arc_discharge_after.png) |
| Impact Bolt | [Physical hit and smaller barrier](impact_bolt_impact.png) | [10% maximum-HP barrier retained](impact_bolt_after.png) |

- [Silent combat clip](mira_rig_combat.mp4)
- [Animated combat GIF](mira_rig_combat.gif)
- [Fixture, before/after resources and source fingerprints](evidence.json)

## Fixture and reproducibility

`python tools/capture_mira_rig_combat.py` creates fresh completed-Mill fixtures
with temporary save/settings files. Caelan begins at 40/140 HP and zero MP;
Mira begins with her ordinary 150 HP / 30 MP. The optional third member, Lucan,
is recruited only into that disposable layout fixture. Cave entry travel and
ATB readiness are shortened so the recording can focus on Mira's controls.

The real authored formation is two level-three Cave Bats. No enemy HP or battle
outcome is edited. No sprite pose, action result or effect is overridden. Every
allocation is applied by the production mouse controls, and every skill/target
is selected through the production menus. The recording demonstrates five
executed actions; it does not claim a complete victory or a full balanced fight.

The MP sequence is 30 → 27 → 23 → 20 → 15 → 11. Repair Pulse genuinely changes
Caelan's local battle HP from 40 to 81, and the completed-action barrier countdown
is visible between the techniques. Tests separately cover durable victory/Flee
settlement, failed-save rollback, defeat and Continue behavior.

See [Mira rig combat](../../MIRA_RIG_COMBAT.md) for full rules and phase boundaries.
