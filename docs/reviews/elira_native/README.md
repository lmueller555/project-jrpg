# Elira native character migration

Named identity is retained rather than assigning an unrelated stock villager. Native 48x72 idles, 4 directions of 8x70ms walks, and the original detailed 72x72 portrait. Unchanged logical registration, body height, collision and plot/schedule state.

## Evidence

- [Actual home scene](live_home.png): live `Game`/`World.draw`, native 960x640, existing Caelan beside the NPC.
- [Idle and all walking poses](numbered.png): own named design and both half-cycles.
- Each walk bank contains normal and half-speed GIFs.
- Explicit compatible contour guides and own costume material details retained with source masters and executable recipes.
- Existing detailed dialogue portrait stays byte-identical and existing social identity keys continue to select it.

## Activation boundaries

The NPC has no bodily household activity clips to migrate. Shelf/climb/retrieve/carry/place artwork in Elira’s story folder belongs to Caelan, not Elira. Those actions are preserved unchanged. Her live behavior remains stationary; the complete walk bank is supplied without adding a schedule or unsolicited movement.

No shared body, playable character, map, schedule, quest, interaction ownership, delivery cue, save format or geometry changes. Actor integration requires the shared RosterArt(named=True) helper. Eight new art-contract tests cover native-density output, exact eight-frame timings, unique poses, conversation interruption/resume, foot/anchor metadata and immutable portraits. Existing household/conclusion tests are run separately to avoid accumulating multiple Game instances in memory.
