# Functional building doors and interiors

This runtime package adds nine exterior doors and eleven actor-free furnished scenes: six cottage interiors, the workshop, mill workroom, and sanctuary hall/bedroom/dining room. It adds no NPCs or quests.

## Runtime behavior

- Approaching the front of a doorway within 30 native pixels opens it. A 38px release radius prevents flicker while standing near the boundary.
- Five poses advance at 100ms intervals. Open and closed endpoints hold; changing direction reverses from the current progress.
- Standing nearby or walking past opens the door without transferring. Walking toward the doorway and contacting its threshold transfers only after it is fully open.
- South-facing cutaway room exits return to the matching exterior. Hall north doors link to the sanctuary bedroom and dining room, with return links.
- Arrival points face into the destination, clear the transfer sensor, and are validated against the 24×12 ground probe. A short transfer cooldown prevents immediate bounce-back.
- Exterior doors are open when Caelan emerges, then close when he leaves. Inactive scene doors close in the background. No action key is needed.

Door panels attach to host building draw passes and do not interrupt smoke, sign, lantern or mill animation. Visible hall doors draw on the room shell. The approved cutaway south thresholds remain visually unobstructed. Smaller rooms center horizontally; floor boundaries, furniture and the wide cottage partition block movement. Town-map markers stay at the current building while indoors.

## Appearance and layouts

The six cottage exteriors reuse their exact approved opening frames. Sanctuary double doors, the workshop, mill and hall door poses hinge/compress the existing closed-panel pixels with nearest-neighbor sampling, retaining their surrounding frames and using the approved dark aperture color. Original art files are unchanged.

Elira uses the approved compact 10×10 layout with the lantern still on its shelf and the stool in place. Halden and the three other standard cottages use separate instances of the approved 13×10 layout. Venn uses the approved 16×10 layout. Sanctuary rooms retain the approved layouts, props, lighting, hearth, steam and room links. There are no review characters baked into these ground images.

The new functional workshop workroom uses the standard shell with a repair bench, table, storage, basin and hearth. The mill workroom uses the wide shell with the sleeping partition removed and storage/sorting furniture. These two layouts reuse existing approved assets; no new furniture or mill machinery art is introduced.

## Files and rebuilding

`doors/` stores five small patch images per visible doorway. `rooms/<id>/map.json` records each separate scene and its portals. Ground frames are shared/deduplicated where layouts match, while scene identity and return links remain independent. Collision is white outside the floor and on solid furniture; walls cannot be bypassed through the decorative void. Approved character frames are drawn dynamically.

Rebuild with `python tools/build_building_interiors.py` after the outdoor map exists, or run `python tools/build_playable_eldenmere.py` to compile both. Pillow is only required for compilation; playing still requires only Pygame. Verify with `python -m unittest discover -s tests -v`.
