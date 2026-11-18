# Native Iselin back-walk source

Status: awaiting user review. This is the rear-direction asset milestone;
existing approved native idles/front/left/right walks and live bindings remain
unchanged.

`keys.png` contains four complete rear contact/passing studies created with
`image_gen.imagegen`. `authored.png` contains sixteen complete new drawings
in row-major chronological order. The approved native back idle controls the
white hair, anatomical-left braid root/bend and anatomical-right mantle. The
previous approved rear animation supplied restrained gait guidance. This is
rear-specific artwork, not a reflected front sprite or detached-limb rig.

The camera is behind Iselin: anatomical left is image left. A foot reaching
forward/away projects higher; a trailing foot toward the camera projects lower.
The same-side arm counters that leg. Opposite contacts exchange the visible
lower hand and the partially hidden higher hand. Foot lift stays narrow and
foreshortened; the braid turns forward from its left-sided root rather than
becoming a central ponytail.

The source master is 1263×1245 with four rows/columns and uneven cell margins.
`tools/export_iselin_native_back_walk.py` hardens alpha at220 and retains the
connected complete drawing. Each head crown/center places an identical
192×288 source window; every whole pose is sampled at exactly1/8 density into
24×36. Transparent window padding accounts for the margins. No boot, limb or
individual occupied height determines scale or alignment. Source crown/waist
relationships were checked alongside final neck, mantle and leg continuity.

After complete-drawing export, the approved stationary back idle head/hair
pixels in rows0–11 are restored at destination y0. The braid bend, mantle,
torso, arms, coat and legs below y12 remain authored pose pixels. This uses the
same documented regional-preservation workflow as the approved front walk;
no moving limb is assembled, translated, stretched or rotated, and no runtime
bob is added. Original generated sources remain unchanged.

Exports use 24×36 RGBA at one artwork pixel per world pixel, draw anchor
`[12,30]`, foot anchor `[12,34]`, unchanged8×4 collision probe and sixteen
35ms frames for the560ms full cycle. The ordinary sheet-based review actor
contains all four approved idle facings and the rear loop, with no HD override.
Source/output hashes and per-frame body windows are in `registration.json`.

See `docs/reviews/iselin_native_back_walk/README.md` for actual movement/rendering
evidence and reproduction. General art guidance stays centralized in
`docs/SPRITE_ANIMATION_STANDARD.md`.
