# MQ03 seated meal poses

Five new seated poses were authored with image generation against the approved
Aldric, Lucan, clerk, driver and Serene sprite references. They preserve each
costume and ordinary body proportions, with bent thighs and knees supported
by the room’s separately rendered chairs. The generated atlas is retained in
`generated_seated.png`; `recipe.json` records extraction rectangles and scaling.

The native exports in `assets/story/regent/poses` use only hard-alpha cleanup
and uniform nearest-neighbor reduction to 24×36 canvases. They do not stretch
or deform existing standing limbs. The draw anchor is (12,30), matching the
room’s existing actor registration. Tomas reuses his approved seated/eating
poses, mirrored by the runtime for the west chair. No new character design is
introduced by this seated posture work.
