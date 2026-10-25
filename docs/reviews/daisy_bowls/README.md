# Daisy's food and water bowls

Matching wooden bowls are installed side by side beside Daisy's rug in Liam's
house. The food bowl is on the left and the water bowl on the right. Both start
full. The implementation is merged into `main` at the user's request.

- [Actual in-game interior](interior.png)
- [Daisy's rug and bowls — close-up](closeup.png)
- [All six full, half-full and empty variants](all_variants.png)

Each native frame is 24×24, with a shallow carved wooden bowl occupying about
16×12 pixels. Wood grain and the lip stay identical across fill states; food
morsels or water remain inside the same recessed area. Half-full states expose
more of the wooden interior. Empty food/water variants share the same appearance.
The colors match the approved furniture and kitchen water palettes.

Full sprites are displayed as single-frame room entities. Their `state_images`
metadata links the three future alternatives; nothing drains, refills or cycles
automatically. No eating, drinking, refill routines or dialogue are added.
Both bowls have small fixed floor blockers, clear caregiver approach points,
and unchanged interaction targets across states. The entry, furniture and rug
remain reachable with all four residents present.

`tools/build_daisy_bowls.py` retains the common wooden body, lip and separate
contents layers. The family-home builder rebuilds the pack and placement.
`tools/capture_daisy_bowls.py` captures the actual game renderer; the room uses
2× scaling, close-up 6×, and variants 14×, all nearest-neighbor.

Validation: **44 focused bowl/home/door/town/social checks pass**. Five new bowl
checks cover six native variants, fixed shells and registration, exact layer/
strip reconstruction, static full-state placement and accessible collision
footprints. The existing household/door checks verify all furniture and exit
routes with the residents and new bowls in place.
