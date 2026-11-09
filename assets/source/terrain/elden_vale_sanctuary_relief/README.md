# Visitor relief room source recipe

The Sanctuary's north-wing visitor room is composed from the existing native
24-pixel Eldenmere floor, limestone, furniture and care modules. It uses the
same crystal-glass windows, branching masonry and warm vigil lamps as the
Sanctuary hall. No generated painting or new character art is involved.

`recipe.json` records original asset paths and SHA-256 hashes, authored room
geometry, furniture ground footprints, the bed approach, the attendant's
station and the reciprocal hall doorway. NPC behavior and rest recovery belong
to the runtime controller; the map only supplies their physical registration.

Rebuild or verify from the repository root:

```sh
python tools/build_sanctuary_reserve_hall.py
python tools/build_sanctuary_relief_room.py
python tools/build_sanctuary_reserve_hall.py --check
python tools/build_sanctuary_relief_room.py --check
```

The hall's new doorway reuses the existing five-frame Sanctuary bedroom door.
Only its small north-wall threshold opens; the hall's public furnishings,
earlier approaches and reserve exit retain their geometry. A native bed plaque
marks the visitor room beside the entrance.
