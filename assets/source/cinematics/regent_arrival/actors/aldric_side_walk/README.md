# Aldric: corrected cinematic side walk

This is **offline part-authored pixel animation**, not a new image generation
and not a runtime skeletal puppet. The original source sheets are never edited.
The standing Aldric from the retained travelers sheet supplies his face, hair,
torso, clothing, sleeve, hand and boot pixels. Explicit joint poses assemble
contact, down, passing and up phases for each leg, with opposing arm swing.

- Eight native 80×96 cells; root anchor `[40,92]` and 32-pixel full stride.
- Stable head/torso registration with a one-pixel settle/rise.
- Fixed 17-pixel thigh/shin lengths and unchanged sleeve/forearm lengths.
- Supporting ankles remain fixed in ground space at authored keyframes.
- Swing boots clear the ground by two or three pixels; cloth has a restrained
  one-pixel lag. No limb stretching or whole-frame morphing is used.
- The authoring recipe includes source/tool hashes, joint coordinates and a
  protected-asset inventory. It does not label new art as user-approved.

The offline authoring script writes the source sheet and recipe; the arrival
exporter copies registered cells without cropping or centering around the feet.
The game streams only the exported PNG frames and their manifest. Pillow remains
an asset-tool dependency, not a new runtime dependency.

The eight poses are deliberately discrete pixel animation: keyframe contact
checks do **not** claim continuous sub-frame foot locking or a perfect physical
simulation. The rear and rear-three-quarter cycles are outside this correction.