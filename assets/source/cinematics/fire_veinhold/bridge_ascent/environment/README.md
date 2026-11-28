# Bridge-ascent environment

`tools/build_prologue_bridge_ascent.py` projects one bridge-local world in metres.
The walking deck is 14 m wide and 299.0819285747636 m long, with 1.2 m rails.
`+Y` points toward the Veinhold, `+X` is the runners' anatomical right and `+Z`
is above the deck. The camera keeps screen right at `-X`: mainland above,
fortress below. It never flips the composition at the vertical camera angle.

The approved close deck, rail and distant mountain materials retain their old
world coordinates. New mainland and ash-island masters are top-surface
materials on fixed land planes; actual cliff sides, boulders, supports, rail
caps/posts and gateway roofs use projected three-dimensional surfaces. They
are not cards tilted to imitate the rising camera.

The sea uses fixed world wave normals and a directional moon reflection.
Projected pixel footprint attenuates unresolved wavelengths, and broad domain
variation avoids the regular diagonal moire of the rejected first blockout.
High camera views also filter the deck material so tiny advancing troops remain
readable at their physical scale. Production bodies are never enlarged.

The transparent X-brace rail material is drawn over the actual underlying sea
and coast. Only sampled occupied alpha enters the geometry depth buffers;
the surrounding rail rectangle is not solid. At sample zero the original
close rail composition retains its exact rounding and matches shot seven.

`ice_projection.json` records the existing guard-removed frozen landing source,
its camera and the inverse-projected visible floor bounds. Only its blue-white
ice coating is reprojected on the deck and matching rail segments at Y 0–3.5 m.
Orange reflections and dark steel are excluded before premultiplied mip
filtering. The source is not extended into a new trail along the bridge.

The previous frontal performance omitted the distant frozen statues and this
landing coating. The ascent preserves that exact initial picture. Correct
fixed high-view sources are restored while outside the frame and return with
the widening view; no statue moves and no anatomy dissolves.

`material_generation.json` retains exact generation prompts, reference hashes
and raw output identities for both new material masters. `performance_recipe.json`
in the parent source directory records actual raw/export/environment input
bytes and every complete native bank output. Use `--verify` for hash/coverage
validation, and `--check` to additionally rerender all 481 samples in both modes.
The baker is serial because its approved close material helper is temporarily
bound to the current camera during each render.
