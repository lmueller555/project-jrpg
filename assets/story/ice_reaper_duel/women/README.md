# Ice Reaper duel — authored women actions

Rhea retains a 128×128 canvas, [64,116] anchor and 82-pixel body registration. The Reaper retains a 192×192 canvas, [96,172] anchor and 155-pixel body registration.

Rhea has eight rear staff-sweep drawings, six front casting drawings, six rear casting drawings and eight directional casting holds. She keeps her staff in her anatomical left hand. The sweep carries that staff across her front toward her right.

The Reaper has six sword-conjuring drawings, six windup drawings, six charging drawings and eight directional sword holds. Her sword remains in her anatomical right hand.

Directional azimuths follow the production stage projection: a profile facing screen right represents -90°, while a profile facing screen left represents +90°. The manifests record this explicitly.

The 96×96 green-eyed Rhea portrait is a dialogue-only asset. The builder also copies it to the scene-local opening/portraits directory required by the cinematic loader.

Rebuild from the repository root:

```sh
python3 tools/build_ice_duel_women.py
```

Source artwork and the generation brief are retained under assets/source/cinematics/ice_reaper_duel/women. Provenance records every extraction and source hash. Each pose is separately authored; registration does not deform character anatomy.
