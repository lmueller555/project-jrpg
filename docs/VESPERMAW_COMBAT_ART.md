# Vespermaw combat art

Vespermaw's dedicated combat bank retains its heavy beast-shaped silhouette:
broad forelimbs and jaw, with mineral shoulder and spine growths. It now depicts
an elemental manifestation of the Sanctuary's disturbed Aether confluence,
channeling Fire, Ice and Water through its fur and crystal growths. It faces
right toward the party. The
[Bestiary entry](BESTIARY.md#vespermaw) owns its level-seven stats, rewards,
affinities and live combat rules. The bank supplies its visual presentation.

The bank uses a shared 160 × 144 native canvas and a fixed anatomical floor
anchor of 64, 128. Per-frame body, contact and cast-origin points travel with
the registered drawing. The renderer uses the complete bank's occupied bounds
to fit every pose between the enemy header and command panel, including the
native-resolution 150% text layout. It uses a grounded boss shadow and samples
anchors on the same clock as their frame.

| Animation | Authored frames | Behavior |
| --- | ---: | --- |
| Idle | 16 | Breathing and quiet weight shifts; looping |
| Prowl | 16 | Heavy articulated walking cycle; looping |
| Raking Claw | 32 | Anticipation, reach, strike and follow-through |
| Confluence Roar | 32 | Throat, jaw and shoulder motion through the roar |
| Gather Resonance | 32 | Planting the limbs and building the charge |
| Charged hold | 32 | Held charge with continuing bodily movement; looping |
| Ruinous Pounce | 32 | Compression, launch, airborne reach, landing and recovery |
| Exhausted | 16 | Slumped breathing and visible fatigue; looping |
| Hurt | 16 | A bodily flinch and recovery |
| Defeat | 32 | Weight settling into the final collapsed pose |
| **Retained body bank** | **256** | **Ten dedicated states** |

The source atlases are retained under `assets/source/combat/vespermaw/`, with
registration and SHA-256 provenance. The deterministic builder extracts whole
authored bodies at one native pixel scale, with shared palette and binary
alpha cleanup. It does not inflate frame counts by generating translated,
warped or mirrored copies. Non-looping states retain their final frame after
their manifest duration; each loop keeps its own manifest clock.

The historical [animation review](reviews/vespermaw_combat/README.md) includes a simultaneous
all-state animated board, contact sheet, a silent production cave renderer
reel, and normal/native enlarged-text captures. The board samples the retained
manifest and verifies that every exported pose was shown.

The 960 × 640 captures and twice-native sprite board are the primary art review.
At minimum resolution with 150% text and three party members, the existing HUD
leaves much less field height, so the enemy is scaled down to keep every pose
visible. The separate compact captures document this layout limit explicitly.

The cave reel is explicitly an **art-only visual fixture**. It renders these
poses through production `BattleScene` using ordinary Bat rules and a directly
sampled enemy pose clock, with a copied level-seven three-character party.
This retained art review predates the live encounter. It does not demonstrate
boss balance or execute its party-wide Roar, marked-target response guarantee,
or recovery vulnerability. It constructs
no persistent Game and touches no user save, settings or quest/reward state.

Vespermaw is now a one-time live encounter in the Echo Chamber. Its current
combat includes party-wide Roar hits, a marked-target response guarantee and
the 50% recovery vulnerability, using these complete animation clocks. The
[live encounter review](reviews/mira_rig_continuity/README.md) captures that
flow separately from the historical art-only fixture. Elemental responses are
now active through the channeling system below. Stagger remains future work.
Those earlier captures do not certify the new elemental presentation.

## Elemental channeling performance

`assets/combat/vespermaw/channeling/performance.json` registers a separate
**72-frame, 2.5-second timeline** using a progression of retained complete body
poses: planted compression, rising shoulders/head, an open-jaw surge, and weight
settling back into stance. New per-frame spine, fur, eye and elemental effects
build on that performance. These are timeline samples with layered animation,
not a claim of 72 newly hand-authored body drawings; the original 256-pose bank
remains unchanged.

The runtime helper `vespermaw_channel_art.py` caches shaded Fire, Ice and Water
palettes for the full bank, so idle, attacks, windup, hurt, exhaustion and defeat
all retain the active form. Fire uses ember-red fur and sparks, Ice frost-white
fur and frost, and Water deep-blue fur and droplets. The silhouette, facial
readability, grounded floor and native scale remain registered throughout.

The free transition begins before every alternate boss turn after its first
two turns. The incoming crystal builds a pulse as the outgoing crystal dims;
aether travels from the crystal into the spine, then through the fur. At
**1.65 seconds**, the active damage profile, fur palette and crystal state
commit together. The body recovers before its scheduled attack begins. The
existing red charging warning remains a separate heavy-attack signal.

Three large embedded wall crystals replace the Echo Chamber's small focal
crystal arrangement: Fire/red, Ice/white and Water/blue, in matching exploration
and battle geography. The active crystal pulses brightly with restrained
rock/boss light spill; the others stay subdued. The chasm and rising aether
remain. Element names and effects communicate the form without revealing its
weakness or recommending a gem. Reduced Motion retains readable form changes
without intense moving effects; pause/focus use the battle simulation clock.

The old art-only review retains source hashes from its original rollout. Its
source-match check targets that historical revision and flags the subsequently
changed Bestiary and renderer in the current tree. Use the live encounter
capture and its `--check` command to verify the current playable implementation.

Reproduce and verify from the repository root:

```sh
python tools/build_vespermaw_combat.py --check
python tools/build_vespermaw_channeling.py --check
python tools/capture_vespermaw_combat.py
python tools/capture_vespermaw_combat.py --check
```

Use `--output /tmp/vespermaw-review` on the capture command for disposable
alternative exports. Retained review verification compares its production
source hashes and artifact hashes; changes to those sources require recapture.
