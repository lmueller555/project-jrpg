# Opening cinematic scenery sources

These unchanged imagegen PNG masters supply the detailed battle-style art for
the late-journey opening frame. The location is a damaged ordinary wayside
sanctuary overlooking inhabited mountain settlements. Its architecture and
landscape do not reveal the ancient or cosmic history.

- `valley_generated.png`: opaque twilight sky and distant valley panorama.
- `valley_alpha_generated.png`: the authored valley and mountains with the sky
  removed by imagegen for independent depth movement.
- `sanctuary_generated.png`: transparent architecture, floor and rubble. The
  bench and lamp were removed by imagegen to permit precise prop registration.
- `props_generated.png`: a low shared stone bench in the upper cell and an unlit
  traveling lantern in the lower cell, both authored on transparent backgrounds.

The generated sources use a wide 2:1 composition. Their exact dimensions and
SHA-256 values are recorded in
`assets/story/opening_cinematic/scenery_provenance.json`.

Run `python tools/build_opening_cinematic_scenery.py` to reproduce the four
960×480 runtime layers. Export consists of nearest-neighbor resizing, transparent
matte cleanup, source-cell crops and registration; the script does not paint
new scenery. Original source bytes remain unchanged.

The sky is the farthest opaque coverage plate and intentionally retains distant
terrain beneath the separately moving alpha valley. Near architecture contains
the precisely placed bench and unlit lamp body. The last 30 rows provide a
shallow foreground rubble layer, with the painted floor retained underneath to
avoid gaps. The actors, lamp flame and other motion are drawn separately by the
cinematic renderer.

The paired acting plane has floor y=375. The bench occupies (633,350,135,26),
with the seat around y=357; the lantern occupies (615,345,18,30), with its runtime
flame centered at (624,363). These registrations keep the existing seated actor
poses in contact with authored scenery.
