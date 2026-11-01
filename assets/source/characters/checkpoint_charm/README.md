# Northern checkpoint small moment

`poses_generated.png` is the retained, unchanged image-generation source for
the existing silver closed-visored road guard. The navy tabard, brass trim,
brown boots and physical-left rectangular shield follow the original guard
sheet. The original portrait and directional idle/greeting assets are unchanged.

Four separately authored walk directions occupy the first four rows. The fifth
row contains a real knee-bent descent into a seated pose; reversing these whole
frames gives the matching stand. The final row checks a supply sack with the
free right hand. No bench or sack is baked into the body sprites.

`tools/build_checkpoint_charm.py` extracts complete cells, removes faint alpha
residue, registers the boot contact at [20,38], and nearest-resizes using one
uniform scale. It never flattens torsos, draws limbs, or mirrors equipment.
`native_review.png` shows every native export at 4×.

```sh
python tools/build_checkpoint_charm.py
python tools/build_checkpoint_charm.py --check
```
