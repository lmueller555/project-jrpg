# Garden and orchard worker art

Implementation review assets, **not user-approved new artwork**. Approved source
appearances (`female_01` and `male_02`) remain unchanged. Regional workers use new
identities; these files do not create or move town NPC instances.

`props_generation.png` is the original image-generation output from 2026-10-31.
It supplied six isolated textured medieval countryside props: a rain barrel with
visible water, empty wicker basket, wooden watering can, drooping potted plant,
apple, and turnip. Prompt requested a three-column/two-row transparent sheet,
three-quarter top-down view, upper-left light, muted wood/iron/leaf colors, and
crisp pixel clusters matching the existing countryside. The original is preserved.

`tools/build_garden_workers.py` exports documented crops to native sizes using
nearest-neighbour sampling and a 128 alpha threshold. This removes the generated
near-transparent edge glow; runtime props have only fully transparent or opaque
pixels. No flat geometric replacement props are used.

Work poses use separate approved head/torso/skirt/leg appearance layers and new
articulated arms. The exporter omits the original swinging arm layers, avoiding
double arms. Four-direction can and pot carries have four walking phases. Weed,
sort, reach, admire and fill poses keep planted feet. Orchard resting has a
new seated lower-body pose. The 40×44 padded canvas retains ground anchor (20,38).
Can, pot, apple and turnip are separate controller-owned props, not painted into
worker frames, so one item has one owner during transfer.

`contacts_native.png` and `contacts_3x.png` are mechanical contact sheets with the
actual exported props placed at their runtime bottom-center offsets. They were
visually inspected for silhouette, alpha, hand contact and character scale.
Gameplay route, depth and bench seating verification belongs to the PR's game
review captures; a contact sheet does not certify those checks.

The current prop registration is recorded in `assets/characters/garden_workers/art.json`:

- Carrying can or plant bottom: actor +(0,-7).
- Watering can bottom: actor +(9,-7); nozzle: can bottom +(10,-13).
- Filling can bottom: actor +(-16,-15), horizontally flipped so handle faces worker.
- Picking apple bottom: actor +(2,-22); admiring: +(0,-18).
- Low sorting/weed contact: actor +(6,-3).

The fill-to-carry transition should interpolate the prop and choose the appropriate
pose at the endpoints. Work sound events must occur at physical contacts.
