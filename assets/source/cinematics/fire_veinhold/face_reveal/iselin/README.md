# Iselin — frontal running reveal sources

> **Superseded performance.** The current selection is
> [source_art_48.json](source_art_48.json), with 48 complete drawings over 800 ms.
> [run_v2/README.md](run_v2/README.md) records current sources and registration.
> Everything below describes the original 24-pose implementation; its masters
> and generation records remain historical evidence.

`source_art_24.json` selects 24 complete frontal running drawings over 400 ms at
60 Hz. Foot labels `near` and `far` preserve the existing Foley contract and mean
anatomical right and left respectively, even in this frontal view. Contact poses
are 0/right and 12/left; the complete drawings progress through support, passing,
toe-off, flight, reach and contact.

The character retains white hair, natural blue eyes, blue/silver travelling
clothes, the mantle on anatomical right/viewer left and the single braid over
anatomical left/viewer right. Natural proportions and detailed painted material
shading follow the frozen-guard cinematic reference. This is a separate cinematic
performance, authored from approved identity references.

Six 2×2 masters retain complete figures. Targeted individual complete-figure
drawings replace atlas cells 1/2/3 and 13/14/15 to bridge arm exchange and keep
recovering boots tucked through early passing. No detached limbs, pasted heads,
warped idles or pixel-interpolated anatomy construct the animation.

`production_generation_24.json` records all generated masters, prompts,
references and hashes. Exact-cell appearance references preserve the key and
neighbor drawings used during authoring. Unselected atlas cells remain history.

`register_sources.py` measures neck, belt and face patches in source-cell
coordinates. It derives uniform whole-drawing density from torso landmarks,
registers the complete image, and records modest whole-body stance/flight recoil.
It does not normalize occupied image bounds or independently transform body
parts. One nearly transparent source fringe receives a recorded alpha-only
cleanup; original source and RGB bytes are retained unchanged.

From the repository root:

```sh
python assets/source/cinematics/fire_veinhold/face_reveal/iselin/register_sources.py
python assets/source/cinematics/fire_veinhold/face_reveal/iselin/write_generation_record.py
python tools/export_prologue_faces.py --actor iselin
python tools/export_prologue_faces.py --actor iselin --check
```

Source inspection covers whole-body anatomy, costume sides, facial identity,
phase chronology and loop seam. Final acceptance also requires the actual native
frontal camera with the other cast; source count or uniqueness does not establish
motion quality or exact foot locking.
