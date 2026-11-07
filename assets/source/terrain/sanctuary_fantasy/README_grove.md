# Sanctuary memorial grove assets

`grove.json` authors the old tree's branching paths, root fan, irregular crown
lobes, silver-green material ramp and source-native leaf material crops. The
existing approved Eldenmere tree supplies irregular leaf shapes at exactly
their native scale; no tree image is enlarged or pasted into the scene. Its
leaf colors are adapted to the Sanctuary's silver-green ramp. Knotted wood,
forks, roots and crown windows are newly authored native geometry.

The landmark uses a shared 192 × 176 canvas and root anchor `(112,164)`. Its
170 opaque pixels stand beside Caelan's 34-pixel visible sprite. The crown leans
west of the root to fit the existing memorial grove and hall composition.
Roots, trunk and canopy are independently placeable modules. The canopy has
six 800 ms poses, whose local leaf highlights change while alpha and silhouette
remain fixed. Woody layers never move. Intentional crown windows reveal sky
and branches. The physical root footprint is `[-12,-12,24,24]` relative to its
anchor, matching the existing Eldenmere tree's ground contact exactly.

Two related saplings use 48 × 72 canvases with anchor `(24,60)` and the same
24 × 24 physical base. Their low root fans make that inherited solid area
visible. Four low blossom/moss modules remain nonblocking; three 8 × 8 petal
families supply simple independent particle poses. No soul, reincarnation or
ancient mechanism identity is assigned to the tree or its lights.

Build with `python tools/build_sanctuary_grove.py`; add `--check` to verify
source fingerprints and deterministic exports without writing. Runtime paths
live in `assets/terrain/sanctuary_fantasy/grove/assets.json`. Its `modules`
records include canvas size, anchor, relative ground footprints, layer intent,
and repository-relative timed frame paths. `landmark_combined` is a derived
review/miniature convenience; production scenery uses the independent layers.

`materials_review.png` compares the tree, Caelan and the two saplings at one
integer enlargement, with native understory details alongside. Original shared
foliage and character assets remain unchanged.
