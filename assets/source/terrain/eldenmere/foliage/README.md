# Eldenmere starter foliage source — approved

`materials_concept.png` retains the original generated one-tree/one-shrub source, guided by the approved cottage-garden scene. Its original remains at `/workspace/generated_images/exec-43e4b083-6dfa-4860-a38e-c3f9eea420c3.png` in the creation workspace. The committed copy is sufficient to rebuild independently of that path.

`recipe.json` records exact source crops, nearest-neighbor sample sizes/positions, native frames, ground rectangles, material ramps, leaf-cluster rectangles, all nine animation poses, scene placements and phase offsets. Tree art occupies roughly 90×92 pixels inside a 96×120 padded frame; the shrub occupies 22×19 inside 24×24. The first tree is about two-and-a-half 36-pixel characters tall in visible art. Wood matches the approved cottage material ramp; the shadow uses existing grass-deep green. Six deeper leaf shades distinguish foliage from grass.

The builder removes the magenta background with an explicit RGB rule and assigns opaque pixels to bark, leaf or ground-shadow ramps before quantization. Bark classification uses source red at least five above green and ten above blue; green pixels below the recorded shadow boundary use the single shadow color. Every exported pixel has hard alpha zero or 255. `parts/<plant>_native.png` retains the sampled rest appearance.

Fixed trunk/branch and shadow layers are separated from leaves. Small polygon masks inside five tree and three shrub rectangles retain source leaf patches; their original places receive a backing one leaf shade darker. These masks never include bark or shadow. Moving patches translate by at most one pixel east and one pixel up; staggered gust/relaxation poses affect groups rather than the entire canopy. Original woody pixels render last and remain identical throughout. Pose zero reproduces the native source exactly.

Nine 600 ms poses produce the 5.4-second wind cycle. The scene retains the approved cottage scene's eighteen 200 ms phases. A 54-frame, 10.8-second review is their first shared repeat: two foliage cycles and three cottage cycles. Instance phase offsets avoid identical neighboring poses without changing wind direction or timing. Existing assets and their exports remain read only; only grass pixels are covered at the selected placements. Review GIFs retain previous pixels and encode frame differences to keep downloads small; decoded pixels and durations are verified against every native frame.

Build: `PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/project-jrpg/bin/python tools/build_eldenmere_foliage.py`.
Test: use the same interpreter with `tools/test_eldenmere_foliage.py`.

This review milestone includes exactly one tree design and one shrub design, instantiated a few times. The tree and shrub appearances and their animations are approved. Additional species, palettes, flowers, grass clumps and reeds remain future work.
