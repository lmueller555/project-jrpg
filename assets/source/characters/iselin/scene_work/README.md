# Iselin scene drawings

These image-generation masters complete the royal replacement without changing the approved 42×72 idles, portrait or four 16-frame walking cycles. Follow [the global standard](../../../../../docs/SPRITE_ANIMATION_STANDARD.md).

- `poses.png`: complete listening, gesturing, turning and seated drawings. The remaining two cells are unused perspective studies.
- `diagonal.png`: sixteen complete rear three-quarter walking drawings in reading order.
- `aerial.png`: north-facing overhead and northwest-facing oblique drawings, without a front-facing face.

Generation references were the approved front, left and rear idle masters. The requested design preserves white hair, blue/silver royal clothing, the right mantle and left-shoulder braid. Each pose was generated as one complete figure. No detached limbs, rotated limb assembly or nonuniform anatomy scaling is used.

Original generation outputs: `exec-22f9aa8e-9034-446a-8a24-5624c79238e5.png` (poses), `exec-e332404c-2920-4dc5-9d10-cb0d78af9040.png` (diagonal), and `exec-d73a27f6-631b-4aa3-8e40-beedd86a7ece.png` (aerial). The retained masters here are the reproducible source files.

`python tools/build_regent_iselin.py --check` verifies extraction, uniform whole-drawing sampling and registration. `registration.json` records source hashes, source cells, silhouette bounds, scales, origins and exported hashes. The diagonal cycle uses one density and a fixed crown grid with a small periodic bob; individual frames are never resized to their boot bounds. Existing approved left/rear cycles are reused for ordinary cinematic walking.
