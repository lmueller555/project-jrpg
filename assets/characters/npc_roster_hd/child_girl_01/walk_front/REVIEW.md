# Twin braids and split skirt · front walk

Eight native 48×72 complete posed outlines manually plotted; no programmable joints, interpolated poses, rotated limbs, idle warp or stretched anatomy. Head/face from approved idle is the only protected source-pixel region (top through y36), shifted by the explicit whole-body bob with matching neck/torso construction. Original braid shape/palette is natively redrawn. Outline, tights, boots, jacket, skirt, hands and sleeves use original palette. Drawing and technical export are separate.

Frame plan (70ms each, 560ms two-step loop): right contact, right down, left passing, left recovery, left contact, left down, right passing, right recovery. Viewer-left is anatomical right. Contact frame1 pairs viewer-left lead foot with viewer-right lead arm. Contact5 reverses. Hands pass neutral in frames3/7. Front depth represented by shortening/lift of trailing/swing boot, not lateral kicking. Fixed artwork draw/ground anchors [24,60]/[24,69], density2. No runtime integration.

Visual drawing findings: identity and proportions are far closer to approved idle than the rejected generated sources. Boots stay beneath hips; complete arm chains remain attached. Braids cover much of sleeve motion, making front arm swing restrained, but no third hands or missing legs. Crown excursions are 18,19,18,17 repeated; shoulders/clasp track the authored bob rather than stretching neck. Contacts place leading boot sole y69; screen-space sole depth changes during stance/recovery intentionally. Uniform source density, no bounding-box rescale. Source skirt dynamics are subtle. Head/hair remain mostly rigid; this is a restrained civilian walk, not expressive animation.

Verification: native bounds/hashes, hard alpha, no side clipping. Normal GIFs exactly 8×70ms; slow 8×140ms. `animation.json` keeps runtime integration disabled. `proof-native.png` and `proof-4x.png` include approved idle. GIFs supplied for motion review; do not treat passing file/timing checks as final visual approval. 

[Numbered frames](numbered.png) · [Native loop](normal.gif) · [Half speed](half_speed.gif).
