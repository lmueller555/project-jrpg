# Mira — front idle

Design status: finalized and approved by the user in chat. Sprite status: draft awaiting visual review.

## Approved design

- Dark brown hair in a short ponytail with a loose fringe.
- A small cream flower with a yellow/gold center above her anatomical left ear (viewer right in the front view).
- Dusty rose pink shirt with sleeves rolled to the elbows.
- Dark charcoal trousers and sturdy brown ankle boots.
- Brown belt and compact tool pouch, with a small gray wrench handle.
- Relaxed, alert front idle; practical clothing for her mechanically minded role.

The ponytail is visible on viewer left. The native flower is a simple 3×3 cross with four cream petals and one gold center pixel.

The front face has two dark single-pixel eyes on the same row. A few fringe pixels have been cleared to skin color so both eyes remain separate from the hair and read clearly at native resolution.

## Files

- `idle_front.png`: transparent native 24×36 sprite.
- `idle_front.json`: frame, foot anchor, design/sprite approval status, layer sources, and template reference.
- `idle_front_review.png`: 24× enlargement on a solid light background for reliable image delivery.
- `scale_comparison.png`: Caelan and Mira together at 16× scale.
- `palette.png`: color swatches extracted from the native sprite.

The generated concept is retained at `../../source/characters/mira/idle_front_concept.png`. Native export uses hard transparency, nearest-neighbor reduction, and a restricted palette sharing existing skin/leather tones, with added pink, charcoal, cream, and gray tool colors. The flower is explicitly preserved as a readable five-pixel motif.

## Shared template workflow

Mira shares Caelan's 24×36 frame and `[12, 34]` foot anchor. Her lower-leg/boot pixels at rows 26–35 are reused exactly from the approved front idle, rather than generating a new leg stance. This reusable component is stored under `../../templates/humanoid_24x36/`.

Three transparent full-frame assembly layers are retained in `../../source/characters/mira/layers/`: head, upper body, and legs. Compositing them in that order reconstructs the native sprite. The upper-body layer currently groups the shirt, arms, belt, and pouch; separate articulated limb layers can be developed when preparing the pose templates for Mira's animation.

Next: review this front idle, then create matching directional appearances and fit them to the approved four-frame movement poses and coordinated head-and-shoulder bob. No Mira animations or other facing directions are included yet. The preserved story documents and Caelan artwork are unchanged.
