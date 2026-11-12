# Page: native overworld registration

The retained generated turnaround follows the existing brown-haired Page in
`assets/story/regent_arrival/actors/portraits/clerk.png`: moss travelling coat,
ivory collar, brass trim, leather document case and boots. The same person now
appears in ordinary MQ03 movement, the shared meal and Sanctuary arrival.

`tools/build_regent_page.py` registers head, coat and boots independently at the
game's native 24×36 scale, then authors eight gait phases and six ledger contact
drawings. It exports the actor sheet, duration/pose manifest and meal pose. All
frames share draw anchor `[12,30]` and ground registration `[12,34]`; the ledger
fits inside that canvas without cropping or a change in character proportions.

Rebuild with `python tools/build_regent_page.py`; use `--check` to verify exports
without writing them. The source hash is checked against `recipe.json` before
export. The ordinary regent builder preserves this approved set and delegates
new Page construction to this recipe rather than recreating a generic villager.

`read` raises and opens the ledger, then holds its last frame. `read_lower`
reverses the contact sequence. Walk phases use explicit 80 ms frame durations.
