# Frontal bridge environment source

The three ImageGen masters retain the frozen-guard scene's painted moonlit
material treatment. `generation.json` records their original generation paths,
prompts, dimensions and hashes. The original masters remain unchanged.

- `backdrop_generated.png`: one tall starry-sky, mountain and coastal painting.
- `deck_generated.png`: the repeating wet riveted-steel material.
- `rail_generated.png`: one transparent X-braced steel railing module.

`tools/build_prologue_face_environment.py` projects those complete painted
surfaces offline using `camera_at` and `project_world` from
`cinematic_face_reveal.py`. World +Y points toward the fortress, +X is the
runners' anatomical right, and Z is upward. The camera tracks ahead of the
party while looking back toward the Merovaran mainland. The bridge is fourteen
metres wide; its rails are 1.2 metres high with a four-metre module repeat.
Deck tiles also repeat every four metres.

A finite masonry approach continues behind the metal bridge's mainland
endpoint and tapers into the painted coastal road. Its material is an
unoccluded road crop from the approved `frozen_bridge_final.png` master;
the crop coordinates and source hash are recorded in the builder and recipe.
This joins the deck visibly to land without shifting a separate mountain layer.

The sky, mountains and coast share one angular projection. The deck and rails
are fixed world planes sampled through exact pinhole-camera rays. Their
perspective and apparent travel therefore agree with the character camera;
the renderer does not slide a flat bridge painting or independently scroll
mountain groups. Premultiplied alpha and continuous mip filtering retain clean
rail gaps and soften distant rivets as they become subpixel. This is painted
surface projection rather than volumetric terrain or character rendering.

From the repository root:

```sh
python tools/build_prologue_face_environment.py --proof
python tools/build_prologue_face_environment.py
python tools/build_prologue_face_environment.py --check
```

Export the current character drawings first with `tools/export_prologue_faces.py`.
The first command writes five native full-performance proofs and a contact sheet.
The full build composites complete authored figures over freshly projected
scenery, then writes 301 inclusive 960×640 full-performance samples, a shared
transparent alarm layer, and camera/manifest JSON under
`assets/story/fire_veinhold_opening/shot07/environment/`. The five-second shot
displays 300 intervals at 60 FPS; the final image supplies its endpoint.
Normal and Reduced Motion share these perspectives because the down-tilt is the
essential face reveal and contains no optional camera shake.

`performance_recipe.json` records actual world geometry, camera settings, source and
output hashes, and a fingerprint of the shared projection helpers. `--check`
re-renders every view from the masters, compares exact PNG bytes, checks PNG
dimensions/chunk CRCs and compares camera/manifest/recipe metadata. Geometry
figures are cinematic staging values rather than a geographic survey.
The original `export_recipe.json` retains the earlier background-only revision.
Runtime streams the new combined bank; its baked marker and performance
signature prevent accepting a stale pose/camera contract. Rebuilding always
starts from the original painted surfaces, avoiding double-composited actors.
