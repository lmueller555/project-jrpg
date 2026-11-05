# Ice Reaper - ice-dome pre-boss cinematic

**Status:** Author-specified scene outline, 2026-11-04. The setting, protective
motive and ordered action beats below are established scene intent. Further
story context and staging after the opening remain open.

**Format:** An action-packed, 45-second cinematic preceding an Ice Reaper boss
fight, using Wintermute2's energetic opening. The first twenty seconds are now
implemented as an isolated Gallery preview; the remaining twenty-five seconds and
playable boss encounter are not implemented.

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

### Ice Reaper visual brief

**Confirmed, 2026-11-04:** She is a woman with an affinity for ice magic who
has merged with a great amount of ice-aspected aether. Parts of her body are
covered in ice. She has glassy blue wings and blue, white and silver accents.

The new artwork follows that brief and remains awaiting visual review.
Silver-white hair and dark clothing are proposed styling choices, not
additional biography, royal identity or a confirmed transformation mechanism.

## Music and timing contract

**Confirmed, 2026-11-04:** **Wintermute2** is the soundtrack for both this
cinematic and the Ice Reaper boss fight.

**Original upload:** [Wintermute 2.m4a](<../../../assets/music/Wintermute 2.m4a>).
The original is unchanged. The full-length
[runtime Vorbis export](../../../assets/music/runtime/wintermute2.ogg) supports
the opening preview; full-cinematic and boss playback integration remain
future work.

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

The current partial preview plays only 00:00-00:20, then returns to Gallery.
Its cue is one-shot playback for that bounded preview, not a decision about
eventual boss-music loop points.

Individual shot lengths after the opening and exact musical accent alignments
remain to be designed. Loop points beyond the full cinematic's handoff,
mixing, and main-story pause/skip/retry behavior are not assigned here.

## Opening and coordinated rescue preview - first twenty seconds

**Implemented:** The opening keeps its portrait dialogue and pixel presentation.
The first five seconds retain the frozen-clearing reveal, with a new sword-equipped
Caelan ready loop. The extension uses authored action sprites matching the combat
cast and a scene-specific perspective stage. Camera movement targets 60 FPS;
character actions contain 4–10 distinct drawings with deliberate timing.

Caelan, Lucan and Mira coordinate a rescue: Caelan cracks Rhea's prison with a
flaming sword, Lucan shields both against the first shard, and Mira destroys a
second shard with her launcher. Rhea opens glowing green eyes and breaks her
prison as a large red rune manifests underneath her. The final shot moves across
the Ice Reaper's shoulders while keeping Rhea central.
The brush parts to reveal a snowy field, the immense ice dome high above and
the frozen castle in the background. Rhea is encased in ice at the lower left.
Above her, the Ice Reaper holds one arm raised with a massive glacial shard
hovering overhead, preparing to launch it.

| Time in seconds | Camera and action |
| --- | --- |
| 0.00-0.90 | Foreground brush clears to reveal Caelan already in his combat stance |
| 0.90-1.20 | Wide view establishes the snowy field, dome, castle, party and frozen Rhea |
| 1.20-1.45 | Camera quickly centers the Ice Reaper |
| 1.45-2.40 | Rapid zoom onto the Ice Reaper and raised shard, with slight camera shake |
| 2.40-2.65 | Brief threat hold; the shard remains charged, not launched |
| 2.65-3.35 | Quick camera move and zoom toward Rhea |
| 3.35-3.85 | Frozen Rhea holds the frame |
| 3.85-5.00 | Caelan's automatic portrait dialogue displays "Rhea! No!" |

| 5.00–7.00 | Ice Reaper aims; Lucan says "Cael, go! I'll cover!"; first shard launches |
| 7.00–7.50 | Caelan and Lucan dash from the party's original position toward Rhea |
| 7.50–9.50 | Slow-motion sword slash and kneeling shield interception |
| 9.50–11.00 | 180-degree perspective orbit reveals Mira at the original position |
| 11.00–12.80 | Push toward Mira loading and aiming her launcher |
| 12.80–14.20 | Camera moves behind the launcher; second shard becomes visible |
| 14.20–15.10 | Mira fires and destroys the second shard |
| 15.10–16.30 | Close-up of Rhea opening green-lit eyes |
| 16.30–17.20 | Prison shatters and the authored red seal starts constructing across the ground |
| 17.20–20.00 | Rune completes; the Reaper rises closer as the unchanged camera sweeps over her shoulders |

At twenty seconds the Gallery preview completes without starting combat or
advancing the saved journey. The full planned cinematic remains 45 seconds.

### Rescue continuity and interception polish

The first shard is aimed at Rhea's upper body, not at Lucan. His raised shield
intersects that same ray before it reaches the prison. The release lowers with
the Reaper's arm, producing a shallower upper-right-to-lower-left approach.
Lucan's longer dash ends on the enemy-facing side of Rhea; his shield, pointed
shard tip, collision flash and fragments share the same contact point.

Actor headings are fixed in world space. Signed camera angles select matching
authored front, side, three-quarter and rear views without swapping weapon
hands or resetting an action's phase. Frozen Rhea keeps facing the party until
she breaks free, then turns toward the Reaper. The final camera follows a real
path behind the Reaper's shoulders, with her image projected from her world
position rather than sliding across the screen.

Lucan remains kneeling and facing the Reaper through his shield raise and
impact; his established late held views are preserved. After Rhea breaks free,
the Reaper uses the earlier approved artwork and rises closer to the camera.
Her head, hair, wings and shoulders form the foreground while her lower body
extends outside the frame. She settles before the shoulder sweep; the camera
path, environment and timing remain unchanged. Rhea stays clear at either
shoulder, with brief natural occlusion during the central crossing.

The rune is an authored seal with a fixed 8.2-world-unit radius. From 16.3 to
17.6 seconds its central seal ignites, branches trace outward, opposing ring
fronts close the circumference, and glyphs activate along those paths. Its
geometry never scales during construction. A completion pulse and restrained
shimmer follow, with emissive strokes lighting the snow beneath cast shadows.

The environment uses one periodic panorama and fixed city, woodland and ruin
locations. Camera direction and projection determine their visibility; shot
labels no longer select different geography or crossfade between landscapes.

Reduced Motion replaces the animated camera moves with static compositions,
removes shake and hovering, and fades the brush instead of sweeping it aside.
Pause and focus loss freeze the same visual clock and soundtrack.

**Replay:** From the title screen choose Gallery, then
**Ice Reaper: Frozen Clearing (20s)** under Scene Studies. The entry is last in
the catalogue: End, then Enter selects it. P pauses, R restarts and Esc returns
to Gallery. The isolated preview cannot alter the saved journey.

Review the [twenty-second clip](../../reviews/ice_reaper_rune_shoulder/preview.mp4),
[keyframes](../../reviews/ice_reaper_rune_shoulder/keyframes.png) and
[verification record](../../reviews/ice_reaper_rune_shoulder/verification.json).
New scenery, boss and ice-effect artwork remain awaiting user review.

Rebuild and capture from the repository root with the existing art dependencies:

```sh
python3 tools/build_ice_reaper_rune.py
python3 tools/build_ice_rescue_men.py
python3 tools/build_ice_rescue_women.py
python3 tools/build_ice_rescue_environment.py
python3 tools/build_ice_reaper_action_audio.py
python3 tools/build_ice_reaper_opening.py
python3 tools/build_runtime_music.py --track wintermute2
python3 tools/capture_ice_reaper_rune_shoulder.py
```

## Named participants

| Character | Specified role in this outline |
| --- | --- |
| Caelan | Enters through the wooded clearing, sees Rhea threatened, and cracks her prison with a fire-charged sword strike |
| Mira | Remains at the original party position, loads her launcher, and destroys the second shard |
| Rhea | Begins encased in ice, breaks free after Caelan weakens her prison, and manifests a red rune; the later planned meteor and vines remain unimplemented |
| Lucan | Rushes past Caelan and shields Rhea against the incoming icicle strike |
| Ice Reaper | Female boss who created the protective dome; threatens Rhea, defends against the meteor and survives the collision |

No additional party member, missing companion's fate, boss identity or
relationship to the existing ruling family is assigned here.

## Opening composition

The reveal needs to communicate three scales and an immediate danger:

- **Regional scale:** The enormous dome overhead and the sprawling, destroyed
  kingdom beneath it.
- **Immediate foreground:** Rhea visibly imprisoned in ice at the lower left.
- **Vertical threat:** The Ice Reaper high in the air above Rhea, with one arm
  raised and a massive glacial shard overhead, preparing to launch it.

Caelan's arrival connects the audience to this view. Individual shot lengths,
camera movements and party blocking after the opening remain to be designed
within the fixed 45-second duration.

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
- Detailed shot plan and per-shot timing for the remaining twenty-five seconds,
  choreography, scale cues and performance.
- Magical sourcing and limits, including how the meteor reaches the dome
  without implying an Aethersphere breach.
- Sound design, score/SFX mix and additional dialogue; the Wintermute2
  assignment and opening 45-second music segment are fixed above.
- Boss-music looping and pause/skip/retry behavior, preserving synchronization.
- Remaining effects, scenery and character-action assets for the later beats.
- Visual and gameplay details of the 45-second handoff: surviving debris,
  arena and actor positions, camera, encounter state and any carried-over
  resource effects. The music continues from its current position.

The full duration and music continuity are fixed. The twenty-second preview's
completion is implemented; the remaining choreography, boss-fight
transition, battle phases, outcomes beyond this survival and post-fight scenes
remain open.
