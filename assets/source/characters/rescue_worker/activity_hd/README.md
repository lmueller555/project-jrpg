# Rescued worker native artwork

This is the distinct trapped/rescued worker from the Sanctuary cave sequence,
not the earlier injured worker, either arrival worker, the caretaker, a party
member or the Sanctuary gardener. Keep the existing script-facing `worker` actor
and `rescue_worker` speaker identities; no personal name is invented.

The existing complete-drawing atlases `actions_authored.png` and
`worker_supported_authored.png` preserve his dark spiky hair, rust shirt, cream
cuffs, dark trousers, boots and supported/injured movement. This bank samples the
retained high-resolution drawings directly at twice the previous artwork density.
It does not scale up old game PNGs or redraw the character as a roster substitute.
No anatomy rig, limb transformation or interpolation is used.

Source cells, connected hard-alpha body extraction, fixed per-bank scale and
original registered origins are recorded in registration.json. The source origin
is doubled without fitting each frame to its newly occupied bounds or lowest
boot. Transparency is hard alpha; there is no color conversion or new palette.
Source hash assertions protect the approved retained identity.

Canvas80×80 native represents logical40×40; draw anchor[20,34] remains logical.
Four supported idles alias the corresponding first walk frame. Four supported
walk directions each keep4×220ms=880ms. Pinned2×500ms, seated1000ms, rise4×300ms
and supported1000ms retain their old looping/hold behavior. There are23 unique
actor rasters; supported shares the final rise drawing. The original male_02
72px dialogue portrait is retained byte-for-byte as portrait.png.

`actor.json` is a standalone dormant CastActor record: travel density2, each pose
density2. It contains no other actor and no prop changes. Activation should
replace only `actors.worker` after loading the existing rescue art registry.
The original rock, tool, dressing, support offsets, collision and story logic
remain unchanged. Arrival caretaker is owned by a separate migration.

Run from repo root with Pillow:

```
python assets/source/characters/rescue_worker/activity_hd/export.py --repo-root .
python assets/source/characters/rescue_worker/activity_hd/validate.py --repo-root .
```

All24 PNGs (including portrait) are reproducible. Native chronological sheets
have been visually reviewed. Production rescue rendering/interaction tests are
required in the separate activation change.
