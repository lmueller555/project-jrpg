# Vespermaw combat art

Vespermaw's dedicated combat bank depicts the Sanctuary cave's pale, heavy
predator: broad forelimbs and jaw, mineral shoulder and spine crusts, and small
violet/cyan microcrystals. It faces right toward the party. The
[Bestiary entry](BESTIARY.md#vespermaw) owns its level-seven stats, rewards,
affinities and intended combat rules; this work supplies visual presentation.

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
| **Total** | **256** | **Ten dedicated states** |

The source atlases are retained under `assets/source/combat/vespermaw/`, with
registration and SHA-256 provenance. The deterministic builder extracts whole
authored bodies at one native pixel scale, with shared palette and binary
alpha cleanup. It does not inflate frame counts by generating translated,
warped or mirrored copies. Non-looping states retain their final frame after
their manifest duration; each loop keeps its own manifest clock.

The [animation review](reviews/vespermaw_combat/README.md) includes a simultaneous
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
It does not demonstrate boss balance or execute Vespermaw's pending party-wide
Roar, marked-target response guarantee, or recovery vulnerability. It constructs
no persistent Game and touches no user save, settings or quest/reward state.

Vespermaw remains unavailable as a live fight until its combat implementation
and story encounter are developed. Its runtime gate remains in place even
with its art attached. Elemental responses and Stagger also remain authoring
data; the crystal colors do not activate elemental mechanics.

Reproduce and verify from the repository root:

```sh
python tools/build_vespermaw_combat.py --check
python tools/capture_vespermaw_combat.py
python tools/capture_vespermaw_combat.py --check
```

Use `--output /tmp/vespermaw-review` on the capture command for disposable
alternative exports. Retained review verification compares its production
source hashes and artifact hashes; changes to those sources require recapture.
