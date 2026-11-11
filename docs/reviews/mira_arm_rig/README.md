# Mira’s wearable arm rig: phase-one art review

These are renders of the **Mira: Aether Arm Rig** entry in the title-screen
Gallery. The study combines the production cave battlefield, combat formation,
character banks, status layout and text renderer with Mira’s new authored rig
poses. The arm equipment is worn over her intact limb.

## Combat compositions

- [Two characters, normal text](combat_2_party_text_100.png)
- [Two characters, enlarged text](combat_2_party_text_150.png)
- [Three characters, normal text](combat_3_party_text_100.png)
- [Three characters, enlarged text](combat_3_party_text_150.png)
- [Weapons 3 / Protection 2 / Support 1 configuration](weapons_configuration.png)

## Animation and effect studies

- [Silent complete animation video](mira_arm_rig_study.mp4)
- [Selected animation GIF](mira_arm_rig_study.gif)
- [Pose contact sheet](pose_contact_sheet.png)
- [Bolt Shot](attack.png)
- [Charged Bolt](charged_bolt.png)
- [Bulwark](bulwark.png)
- [Repair Pulse](repair_pulse.png)
- [Impact Bolt](impact_bolt.png)
- [Arc Discharge](arc_discharge.png)
- [Fixture, resource and asset evidence](evidence.json)

## Scope and controls

This is an **art preview**, rather than a played battle or an implementation of
the future techniques. The disposable composition has Caelan and Mira facing
two level-two Cave Bats. Its optional third character is Lucan. The preview
explicitly supplies no bot loadouts; this does not remove the bot system from
ordinary combat. No model actions, damage, healing, MP costs, skill unlocks,
battle results or rewards execute. Character HP, MP and progression remain
unchanged. Projectiles, barriers and repair/electric effects are seekable visual
sketches attached to the arm rig’s authored registration points.

The rig panel has six local power units, W/P/S channels, draft changes and
Apply/cancel controls. Changing its allocation affects only this UI study.
The skill-art buttons select poses and show proposed W/P/S minimums; they do
not enforce requirements or execute skills.

In the Gallery:

- Click a skill-art button to view its animation.
- **[ / ]** steps through all poses, including reactions and movement.
- **Space** holds or resumes the pose cycle and the Gallery countdown.
- **3** switches between two- and three-character compositions.
- **Tab** focuses routing, then Tab or Up/Down selects a channel.
- **Left/Right** removes/adds a unit; Enter or focused Space applies a complete
  six-unit allocation.
- **Escape** first cancels a focused routing edit, then returns to the Gallery.

The automatic study returns after 45 unheld seconds and can be restarted.
Focus loss freezes the study and clears held controls. Reduced-motion mode uses
one representative drawing per pose with static illustrative effects.

Reproduce with `python tools/capture_mira_arm_rig.py` in the configured Pygame
environment. The tool writes only this review folder and the Gallery thumbnail;
the Game instance is non-persistent and uses no user save or settings path.
