# Caelan — overworld artwork and runtime registration

[animation.json](animation.json) is the runtime source of truth. All four
approved HD idles, walks and runs are integrated. Existing `review_hd/` paths
remain stable; no approved PNG was moved, resized or redrawn for integration.

| Bank | Artwork pixels | Logical canvas | Timing | Logical draw anchor |
| --- | --- | --- | --- | --- |
| Idles | 48×72 | 24×36 | Stationary | [12,30] |
| Walks | 48×72 | 24×36 | 16×35 ms = 560 ms | [12,30] |
| Front/rear runs | 48×76 | 24×38 | 16×25 ms = 400 ms | [12,32] |
| Left/right runs | 56×76 | 28×38 | 16×25 ms = 400 ms | [14,32] |

Every travel bank declares density 2. `Player.draw_anchor` selects the current
bank's normalized anchor; scene-specific `story_draw_anchor` retains priority.
The added run padding changes neither visible body scale nor gameplay position,
collision, movement speed, camera coverage or interaction reach. Native detail
survives composition in ordinary worlds and the regional overworld. Stopping,
blocking and gait/direction changes retain the existing clock-reset behavior.

The rescue display actor inherits current HD idles and 35 ms walking frames.
Cup delivery uses the current HD travel banks with bounded four-phase logical
hand guides; it no longer loads a second legacy walking bank. Unique household,
carrying, casting, rescue/support, seated and combat poses retain their own
artwork, prop cues, densities and anchors. They have no replacements among the
new locomotion drawings and are not superseded travel banks.

Superseded 1× idle/walk/run PNGs, strips, manifests, unused old limb sources,
travel-only previews and obsolete exporters were removed. Git history retains
those versions. [retired_travel.json](retired_travel.json) records deleted paths,
hashes and intentional retirements from preservation contracts; every current HD
sprite remains protected. Source atlases and old prop layers still needed by
unique scene-action recipes remain source inputs, not selectable travel banks.
The old 1× travel exporter cannot recreate retired banks.

Old terrain and companion review recipes use `tools.caelan_reference.open_image`
to sample current HD references explicitly into their existing logical review
canvases. Historical filename keys are compatibility inputs to that offline
adapter; no old travel images are loaded or recreated. Gameplay uses density-aware
loaders instead. Explicitly retired source hashes remain recorded provenance.

[Run integration captures and validation](../../../docs/reviews/caelan_run_integration/README.md)
cover actual Player movement in town, hall and cave, gait transitions, foreground
occlusion and cup delivery with temporary saves. Stylized foot sliding remains
an observation, not an integration failure or an invitation to change gameplay
speed or distort approved anatomy.
