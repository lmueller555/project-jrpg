# Mira: wearable arm-rig artwork (phase one)

Mira's combat bank now depicts a worn external forearm rig: a graphite housing,
brass actuator and projector plates, leather attachment straps, an aether lens,
and visible intact hands and arm. Her rose work shirt, flower, ponytail, tool
belt and boots retain her existing character identity. The machinery is worn;
it does not replace a limb.

## What this phase delivers

The production combat sprite loader uses the revised idle, firing, guarding,
hit, rig-operation, victory, KO and movement drawings. The ordinary Bolt Shot
retains its existing release, damage-impact and action timing. The historical `overclock` animation slot depicts cuff operation and remains
available to the art sampler. Phase two replaces that old action with the five
live rig techniques; the retained animation name does not grant a combat skill.

Five additional eight-frame technique studies provide preparation, activation,
recoil or hold, and recovery: Charged Bolt, Bulwark, Repair Pulse, Impact Bolt,
and Arc Discharge. These began as art-only studies. [Phase two](MIRA_RIG_COMBAT.md) now implements
them as power-gated combat skills; the Gallery remains an isolated art sandbox.
Each source drawing is retained, registered at the feet and exported with
attachment anchors for the emitter and controls. Exporting resamples and
registers the authored artwork; it does not synthesize anatomy or use whole-body
warping to manufacture additional poses.

The Gallery entry **Mira: Aether Arm Rig** presents those drawings in the actual
cave battle renderer with a local power-routing console. Its six units begin at
Weapons 2 / Protection 2 / Support 2. Minus releases a unit, plus assigns a free
unit, and Apply commits only a complete six-unit allocation. Cancel restores
the applied values. Channel icons and numeric values supplement the orange,
cyan and green colors. The console is preview-local and does not alter damage,
MP, ATB, learned skills, inventory, quests or saved data.

The preview can switch between two- and three-member compositions and seek or
hold individual poses. Its effect sketches are anchored to the rig and explicitly
illustrative. The composition omits the old companion bot. Phase two also retires its live
combat participation; phase three completes the remaining narrative/asset cleanup.

## Boundaries and follow-up

Phase one changed combat artwork and added an isolated Gallery study without
changing stats, action costs, balance, narrative or save formats. Phase two now
adds the live rig rules and save owner described in [Rig combat](MIRA_RIG_COMBAT.md).
Existing story/world weapon props remain until the coordinated narrative and
continuity cleanup.

[Phase two](MIRA_RIG_COMBAT.md) adds the live rig owner, skill power requirements,
ally support, barriers, action resolution and save compatibility. Phase three completes
the retired bot's removal across story, ownership, compatibility, asset builders,
documentation and current review evidence.

See the [visual review](reviews/mira_arm_rig/README.md) for captures and the
[source registration](../assets/source/combat/mira_arm_rig/README.md) for provenance
and rebuild instructions.
