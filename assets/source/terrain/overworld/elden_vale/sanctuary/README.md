# Elden Vale Sanctuary overworld art

`recipe.json` assembles the regional icon from the same native pixel modules as
the detailed reserve: the pale hall and cloister, silvery memorial tree, natural
cave stone and asymmetric amethyst/cyan/opal crystals. Each complete component
is reduced uniformly with nearest-neighbour sampling. Small, disconnected
ground footings use the exact regional meadow tile and dirt approach material;
transparent gaps leave the surrounding world visible. No flat emerald island,
scene painting or extracted scenery silhouette is used.

The builder records the actual module images, library manifests and stone-kit
inputs with their hashes. The component layout and original registration are
retained in the recipe. The old `generated_miniature.png` remains only as an
archived earlier design reference and is not read by this pipeline.

Run `python tools/build_overworld_sanctuary_art.py`, or pass `--check` to verify.
The 96×80 miniature is smaller than Eldenmere's 144×120 sprite. It has binary
alpha and an irregular silhouette. Its `[32,74]` foot anchor, collision-free prop
contract and regional travel behavior are unchanged.
The approach uses the ordinary dirt path; the former standalone steps are no
longer exported or placed because the overworld has no matching height change.
