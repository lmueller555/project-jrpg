# Crown soldier frontal run revision

The 48 complete source drawings selected by `../source_art_48.json` replace the
former 24-pose, 400 ms performance for the cinematic face reveal. This is an
internally reviewed implementation for the player's in-game Gallery review,
not a claim of prior user approval of these new drawings.

`frame_XX.png` files are unmodified complete ImageGen output masters. The
corresponding prompt and generation JSON preserve tool/generation provenance.
No detached limbs, animation rigs, image warps, duplicate-pose filling, or
crossfaded anatomy is used. Sword and shield are painted into their complete
drawings with correct anatomical ownership. The forward arm authoring guide
was supplied to image generation to correct the pump; its colored marks never
enter production artwork.

The run is 800 ms with right contact at frame 0 and left contact at frame 24.
The right sword arm travels rear 0 → neutral 12 → forward 24 → neutral 36 →
rear 48; the left shield
uses a smaller counterbalance. Source keys were inspected before in-betweens.
The first attempted 8-cell consecutive sheet interpreted the requested interval
as broad full-cycle keys. It is rejected under `history/`, rather than being
reordered or interpolated into a production cycle. Later whole-frame repairs
corrected support-leg identities, swing-knee recovery and safe blade carry.

The companion global sprite standard remains authoritative. This file records
only this asset's implementation facts and reproduction command:

```sh
python assets/source/cinematics/fire_veinhold/face_reveal/crown_soldier/run_v2/register_source.py
```

Registration measures painted eyes, throat and buckle with normalized
cross-correlation. A fixed 0.60 uniform whole-master density and eye-based
translation preserve source proportions. Modest phase-authored translation
follows support and flight; there is no runtime bob or foot/occupied-height
normalization. Neck/belt measurements audit the model independently, including
flight drawings. The density matches the former bank's 240 artwork pixel
eyes-to-belt model, rather than fitting any pose's occupied height. The
exporter removes only alpha at 16 and below before premultiplied
whole-figure sampling, retaining source masters unchanged.

`registered_contact_sheet.jpg` and `registration_report.json` support internal
anatomy/continuity review; Gallery travel and full-film checks are documented
by the integration review under `docs/reviews/veinhold_running_polish/`.
