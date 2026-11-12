# Sanctuary response identities and rope authoring

`care_identity_design.png` is the retained reference-directed design sheet.
The gray-haired caretaker wears ivory linen and a teal service sash; Worker A
has black hair and rust workwear with a supported forearm; Worker B has brown
hair and olive workwear with a wrapped calf. Their portraits use the same
faces, clothing, and injury details. The separate gray-haired survivor who
returned to Eldenmere retains his existing assets.

Rebuild with:

```
python tools/build_sanctuary_arrival_art.py
python tools/build_sanctuary_arrival_art.py --check
```

The exporter removes only connected gutter pixels, registers each native body
to the established foot baseline, and retains original contact-leg poses for
caretaker walking. Larger action canvases use explicit pose anchors; they do
not change the body's world position. Worker B has a wider native resting
canvas to accommodate his supported leg without clipping or shrinking him.

The rope and posts are separate assets. Both new timeline tracks last 1600 ms:
there are 16 rope drawings and 12 caretaker drawings. At 300 ms the caretaker has
grasped the fastening, at 400 ms the free end is unhooked, and from 300–1000 ms
seven consecutive grip positions match the free rope end exactly in world
space. After release, gravity carries the slack toward its fixed anchor; the
loose coil settles beside the left post. No wooden post is transformed.

The rope's closed/open composites match runtime layering: rope first, fixed
posts last. The source recipe retains the design and original post-art hashes.
