# Caelan directional runs — approved

Front, right and back runs were approved by the user after the four-direction preview.
The existing approved left run is retained exactly. Each direction has four native
24×36 RGBA frames, 100 ms per pose and foot anchor [12,34].

- [All four runs](all-directions.gif) · [slow pose inspection](all-directions-slow.gif).
- [Front poses](front-poses.png) · [Right poses](right-poses.png) · [Back poses](back-poses.png).

Right-facing limbs share the approved left geometry; its own idle provides the head
and costume. Front and back use foreshortening, opposing bent arms and alternating
contact/flight. Native assets live in `assets/characters/caelan/run_DIRECTION/`.
Editable source layers are four-cell strips under
`assets/source/characters/caelan/run_DIRECTION/`; each cell is 24×36 and layer order
is recorded in each animation's per-frame metadata.

Rebuild with `python tools/build_caelan_directional_runs.py` (Pillow).
Validate with `python -m unittest discover -s tests -p 'test_caelan*run*.py' -v`.
`approval.json` retains the reviewed frame hashes and protected original assets.

These are animation assets. Player selection of run frames is a separate runtime change.
