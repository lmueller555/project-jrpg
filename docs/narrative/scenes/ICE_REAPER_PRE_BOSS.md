# Ice Reaper - ice-dome pre-boss cinematic

**Status:** Author-specified scene outline, 2026-11-04. The setting, protective
motive and ordered action beats below are established scene intent. Further
story context, staging and implementation remain open.

**Format:** An action-packed, 45-second cinematic preceding an Ice Reaper boss
fight, using Wintermute2's energetic opening. This is not a playable combat
script or an implemented cutscene.

**Placement:** Unplaced. The kingdom, world region, act and installment have
not been assigned. Integration must respect or explicitly revise the
[current Game I scope](../game_01/ACT_OUTLINE.md); this outline does not
silently establish new political geography or a later-act plot.

Related references: [scenario index](../game_01/SCENARIOS.md),
[Caelan](../game_01/characters/CAELAN.md),
[Mira](../game_01/characters/MIRA.md),
[companion foundations and approved appearances](../game_01/COMPANIONS.md)
and [aether foundations](../../FOUNDATIONAL_LORE.md).

## Setting and background

A huge ice dome covers an entire region. The Ice Reaper created it over her
kingdom to protect it against a hostile army.

The cinematic takes place **underneath this dome**. Beyond the wooded approach,
the view opens onto the kingdom, now destroyed and covered in giant ice shards.
The relationship between that destruction, the hostile army and the dome's
creation is not yet specified.

The dome is a regional ice construction, **not the Aethersphere**. Breaking
through its ice does not establish a breach of the planet's atmosphere or
reveal the Aethersphere's hidden nature.

## Music and timing contract

**Confirmed, 2026-11-04:** **Wintermute2** is the soundtrack for both this
cinematic and the Ice Reaper boss fight.

**Original upload:** [Wintermute 2.m4a](<../../../assets/music/Wintermute 2.m4a>).
Keep this original unchanged; runtime export and playback integration are
future implementation work.

| Item | Requirement |
| --- | --- |
| Full cinematic duration | Exactly **45.0 seconds** in an uninterrupted playthrough |
| Cinematic music | Wintermute2 from **00:00.000 to 00:45.000**, its extremely energetic intro |
| Start | Begin the cue at track position zero with the cinematic |
| Boss-fight handoff | At **00:45.000**, continue the same cue into combat without restarting the song or replaying the intro |
| Timing budget | All twelve beats, dialogue, reaction holds, impact accents, fades and transition time fit inside the 45 seconds |

The cinematic is timed to the music, not extended by click-to-continue
dialogue or an additional end hold. The final ice-energy blast must resolve
within that budget so the boss fight follows without a gap in the score.

Individual shot lengths and musical accent alignments remain to be designed.
Loop points beyond the initial handoff, mixing, and pause/skip/retry behavior
are not assigned here.

## Named participants

| Character | Specified role in this outline |
| --- | --- |
| Caelan | Enters through the wooded clearing, sees Rhea threatened, and frees her with a fire-charged sword strike |
| Mira | Present as a party member; her specific actions and positions remain to be developed |
| Rhea | Begins encased in ice, is freed, then answers with a red-rune meteor cast and massive restraining vines |
| Lucan | Rushes past Caelan and shields Rhea against the incoming icicle strike |
| Ice Reaper | Female boss who created the protective dome; threatens Rhea, defends against the meteor and survives the collision |

No additional party member, missing companion's fate, boss identity or
relationship to the existing ruling family is assigned here.

## Opening composition

The reveal needs to communicate three scales and an immediate danger:

- **Regional scale:** The enormous dome overhead and the sprawling, destroyed
  kingdom beneath it.
- **Immediate foreground:** Rhea visibly imprisoned in ice.
- **Vertical threat:** The Ice Reaper high in the air above Rhea, charging an
  icicle strike.

Caelan's arrival connects the audience to this view. Individual shot lengths,
camera movements and party blocking remain to be designed within the fixed
45-second duration.

## Ordered cinematic beats

### Beat 1 - Caelan reaches the clearing

Caelan emerges through a clearing in the woods. The wooded approach gives
way to the sprawling view beneath the ice dome.

### Beat 2 - The kingdom and the immediate threat are revealed

The kingdom fills the background, destroyed and covered in giant ice shards.
Rhea is encased in ice in the foreground. High above her, the Ice Reaper
charges an icicle strike.

### Beat 3 - Caelan reacts

Caelan sees the danger to Rhea and exclaims:

> **Caelan:** "Rhea! No!"

This is the only dialogue specified so far.

### Beat 4 - Lucan moves to protect Rhea

Lucan rushes past Caelan and places his shield between Rhea and the strike.
He guards her while Caelan moves in to free her.

The exact release, interception and impact timing of the icicle strike remain
staging details; Lucan's protective action must be clear.

### Beat 5 - Caelan breaks Rhea's ice prison

Caelan charges his sword with fire, dashes in and strikes the ice encasing
Rhea. The ice shatters, freeing her.

The target of his strike is the ice prison, not the Ice Reaper. This is a
forceful shattering rescue, not a gradual thaw.

### Beat 6 - Rhea turns her distress into determination

Rhea is extremely upset and determined to prove her magical prowess against
the Ice Reaper.

That emotional state drives the following attack. No additional dialogue,
past humiliation or permanent change to her personality is prescribed.

### Beat 7 - The red rune and meteor

Rhea summons a huge red rune beneath her feet and calls forth a huge meteor
from the sky.

### Beat 8 - The meteor breaks through the dome

The descending meteor crashes through the ice dome on its way toward the
Ice Reaper. The breakthrough must read against the dome's enormous scale.

A penetration is specified; complete collapse of the regional dome is not.

### Beat 9 - Rhea prevents the Ice Reaper's escape

Before the meteor reaches the Ice Reaper, Rhea summons massive vines and
latches them onto her, preventing her from escaping the impact.

The Ice Reaper is still airborne in this phase. The vines must visibly
restrain her rather than allowing an unexplained dodge or relocation.

### Beat 10 - The Ice Reaper encases herself

Just before collision, the Ice Reaper encases herself in ice.

This defensive shell is distinct from the ice prison that previously held
Rhea. The exact appearance and interaction with the vines remain open.

### Beat 11 - Collision and ground crash

The meteor collides with the encased Ice Reaper. She and the meteor crash
into the ground.

The impact location, party clearance and immediate debris choreography
remain to be developed.

### Beat 12 - Survival and the ice-energy blast

The Ice Reaper survives. She blasts the meteor rubble away with a huge flash
of ice magic energy.

This is the final specified beat. The spectacle has not defeated her; the
boss fight still lies ahead.

## Character and staging priorities

- Caelan reacts to a companion in danger and acts decisively to rescue her.
- Lucan's shield work creates the opportunity for that rescue. His role should
  be readable in the action, without an explanatory speech.
- Rhea's response is emotionally charged and motivated by proving her prowess.
  Preserve that intent rather than recasting it as a calm demonstration.
- Mira remains part of the encounter. An unassigned action beat is not a
  decision that she stands idle throughout the cinematic.
- Keep the causal order legible: threat, protection, rescue, Rhea's
  counterattack, restraint, defensive shell, collision, survival.
- Attribute the red rune, meteor and vines to Rhea. Distinguish the two ice
  encasements and keep the Ice Reaper's position readable across the aerial
  attack and ground impact.

## Fast anime-style presentation

The entire sequence must convey its action within Wintermute2's opening
45 seconds. Use quick shots and anime-style bursts of movement across
characters, objects and the camera rather than extending the cinematic.

- **Characters:** Use rapid acceleration and decisive stops, directional
  smears, speed lines or afterimages for Lucan's rush and Caelan's dash.
  Land on readable poses for the shield guard, sword strike and Rhea's casting.
- **Objects and effects:** Give the icicle strike, breaking ice, meteor,
  vines and rubble fast, clearly directed motion. Preserve a brief readable
  moment for contact, restraint or a change of state.
- **Camera and editing:** Use whip pans, snap moves, fast tracking, snap zooms
  and quick cuts to connect the action. Resolve movement onto the important
  subject instead of keeping the camera in constant unreadable motion.
- **Impact accents:** Brief impact frames, shake or hit-stop can emphasize
  shattering ice, the dome breach, the ground collision and the final blast.
  These accents consume time inside the 45-second budget; they are not extra
  holds. Avoid continuous strobing or shake that obscures the choreography.

Speed must not remove necessary information. The regional dome and ruined
kingdom still need an establishing view; Rhea's distress and determination
must register before her counterattack. Keep screen direction and the chain
of protection, rescue, casting, restraint and survival clear.

These are presentation requirements, not a finished shot list or new approved
animation assets. No additional dialogue is assigned.

## Continuity and magical limits

The [established aether rules](../../FOUNDATIONAL_LORE.md#1-foundations-of-existence)
still apply. This outline specifies visual intent, not unlimited energy,
creation of matter from nothing or access to the Aethersphere.

The meteor's material source and arrival, the vines' source and growth,
the regional dome's energy requirements, and the party's available power
at this point need to be worked out later. Preserve the requested action
while designing those explanations; do not silently replace the meteor
or remove the dome breakthrough.

These cinematic actions do not register new skills, assign unlock levels,
define friendly-fire rules or determine HP, MP or damage. Rhea's presence
also requires appropriate placement relative to her eventual recruitment.

The Ice Reaper's survival here does not establish general invulnerability.
Her protective motive remains part of the background; the ruin's cause and
the kingdom's inhabitants' fates are not settled.

## Details to develop next

- Kingdom and region names, political context and exact story placement.
- Why the party confronts the Ice Reaper, how Rhea was encased before Caelan
  arrives, and the hostile army's identity and current situation.
- Mira's contribution, positions and interaction with the other party members.
- The Ice Reaper's appearance, personal history and precise relationship to
  the kingdom; no identity as an Ancient is assigned.
- How the protective-dome backstory is conveyed to the player.
- Detailed shot plan and per-shot timing within the fixed 45 seconds,
  choreography, scale cues and performance.
- Magical sourcing and limits, including how the meteor reaches the dome
  without implying an Aethersphere breach.
- Sound design, score/SFX mix and additional dialogue; the Wintermute2
  assignment and opening 45-second music segment are fixed above.
- Boss-music looping and pause/skip/retry behavior, preserving synchronization.
- Effects, scenery and character-action assets needed for implementation.
- Visual and gameplay details of the 45-second handoff: surviving debris,
  arena and actor positions, camera, encounter state and any carried-over
  resource effects. The music continues from its current position.

The duration and music continuity are fixed; specific transition choreography,
battle phases, outcomes beyond this survival and post-fight scenes remain open.
