# Caelan left facing run — approved

The user approved the revised left-facing run with a 1–2 pixel wider arm swing.
Four native 24×36 RGBA poses play at 100 ms each, with foot anchor [12,34].
Bent opposing arms, forward lean, folded recovery legs and two flight poses distinguish it from walking.
Shoulders remain anchored. The head, torso, legs and timing match the initial reviewed proposal.

- [Walk beside approved run](walk-vs-run.gif): independent 140 ms walk and 100 ms run clocks.
- [Slow comparison](walk-vs-run-slow.gif): corresponding poses held for 350 ms.
- [Four poses](run-poses.png).

Native frames and strip: `assets/characters/caelan/run_left/`.
Editable layers: `assets/source/characters/caelan/run_left/`.
Rebuild: `python tools/build_caelan_left_run.py` (Pillow).
Validate: `python -m unittest discover -s tests -p test_caelan_left_run.py -v`.

This commits approved animation art only. Other running directions and player run selection remain future work.
`approval.json` records the approved native frame hashes and unchanged pre-existing Caelan assets.
