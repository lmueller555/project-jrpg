# Caelan directional runs — historical approval record

New or revised runs follow the [running animation standard](../../VISUAL_ART_STANDARD.md#running-animations).
This page preserves the original four-direction review, not a template for
building new limbs or a statement of the current runtime bank's approval.
See the [current Caelan asset inventory](../../../assets/characters/caelan/README.md)
for the retained legacy runs and planned HD work.

The original front, right and rear runs were approved after the four-direction
preview; that review retained its approved left run. Each historical direction
used four 24×36 RGBA frames,100 ms per pose and foot anchor `[12,34]`.

- [Original all-direction comparison](all-directions.gif) · [slow inspection](all-directions-slow.gif).
- [Front poses](front-poses.png) · [Right poses](right-poses.png) · [Rear poses](back-poses.png).

`approval.json` retains the original reviewed-frame hashes and protected inputs.
The old four-cell layered sources remain under
`assets/source/characters/caelan/run_DIRECTION/` as historical evidence. Their
part assembly and reflected geometry are superseded as authoring instructions
by the complete-drawing workflow in the central standard. Approval evidence,
previews and source assets are unchanged.

The current runtime already selects four-direction legacy runs; the old
statement that player run selection was future work is obsolete. This cleanup
changes documentation only and does not replace any runtime frame or builder.
