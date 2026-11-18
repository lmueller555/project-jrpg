# Cottage interiors — approved size and layout templates

Status: APPROVED SIZE AND LAYOUT TEMPLATES. The user approved 10×10, 13×10 and 16×10 furnished interiors at a common pixel scale, retaining larger separate room maps. The three arrangements are approved; named household assignments remain future work. This document does not change narrative canon or define playable engine maps.

## Size rule

Use the user-selected 10×10, 13×10 and 16×10 floor envelopes. These replace the earlier 6×6, 8×6 and 10×6 review after the user found those rooms too small. All three keep a common ten-tile depth and increase in width by three tiles per cottage tier. Door and chimney positions still project proportionally from each corresponding exterior; floor dimensions are no longer constrained to twice the exterior footprint. The 24px terrain grid and 24×36 character scale remain fixed.

| Cottage | Approved exterior ground | Proposed interior floor | Native floor pixels | Floor tiles |
| --- | --- | --- | --- | --- |
| Compact | 3×3 | 10×10 | 240×240 | 100 |
| Standard | 4×3 | 13×10 | 312×240 | 130 |
| Wide | 5×3 | 16×10 | 384×240 | 160 |

These dimensions describe the usable floor envelope before furniture or partitions. Projected north-wall height, cutaway walls and surrounding void are additional rendering space. A partition or utility nook consumes this same budget; it does not silently add floor area. The existing 10×8-floor review room remains an asset showroom and is not assigned to a cottage size. The approved size templates are separate exports, preserving the original asset showroom and artwork.

## Layout character

- Compact: one main living/sleeping room, one bed or a compact sleeping corner, a small dining arrangement and a short cooking corner. Choose the cupboard or narrow pantry to avoid overfilling the room. Use furniture placement to distinguish areas.
- Standard: shared living/dining space with a clear sleeping side, counter and washbasin, and room for modest storage. A short divider or doorway may separate a nook if access still fits the envelope.
- Wide: a larger shared dining area, family sleeping arrangement and optional partitioned bedroom or work/storage nook. Extra width creates useful activity areas; it does not enlarge the furniture sprites.

Keep a continuous route from entry to every usable furnishing. Aim for 48px on main circulation routes and at least 24px clear on short approaches. Measure character movement by its eventual ground collision footprint rather than its entire 36px projected height. Leave usable floor in front of cupboards, basin, pantry, beds and chairs. Decorative wall shelves do not block the floor below them.

## Exterior continuity

Map the entry to the exterior door's relative horizontal position; the compact door is offset left and the wider door is right of center. Locate a household's hearth and flue to agree with its exterior chimney. Place windows on their corresponding walls; visible north-wall windows are rear windows, while the exterior's front windows belong to the cutaway south wall. Do not copy the current showroom's fixture positions automatically. Cottage palette variations can share layouts; matching wood/plaster accents can link each interior to its exterior without four different floor plans.

The sanctuary is a separate building and layout problem. It should not be squeezed into a cottage-size rule or assigned a cottage exterior without an explicit design decision. Do not assign the cottage sizes to Halden, Elira or the Venn family yet; choose those assignments when planning their quest scenes.

## Current kitchen review

The user selected kitchen counter, washbasin and pantry storage as the next asset set. These are static reusable furnishings at the existing pixel scale. The counter is 48×48, basin stand 24×36 and narrow open pantry 24×48, all with transparent registration padding. They reuse approved materials.

The new 10×8-floor kitchen showroom places counter and basin under the right window and the pantry below the wall shelf. The original cupboard moves beside the bed. Only one dining chair is shown; the other three facing-comparison samples remain in their approved pack. Bed and table keep their positions; all approved sprite files remain unchanged. This illustrative arrangement is not a proposed final cottage floor plan.

The kitchen asset set is approved. The new `assets/terrain/eldenmere/cottage_layouts/` pack implements the three approved furnished layouts with a same-scale exterior/interior comparison. All furnishing approaches and Caelan's foot anchor are reachable using a conservative 24×12 floor probe. The wide cottage uses a longer cutaway sleeping/storage divider, one bed and three dining chairs. Existing furnishings are redistributed across the larger floors without resizing their artwork. The size, density, access and exterior alignment are approved. Household-specific variants remain future work.
