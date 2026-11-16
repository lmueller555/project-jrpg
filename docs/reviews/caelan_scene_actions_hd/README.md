# Caelan scene-action migration

Caelan’s ordinary scene poses now use complete drawn 2× bodies: waking,
sitting/standing, eating, passing the breakfast cup, four-direction holding,
carrying and handovers, workshop/casting work, lantern retrieval/placement and
cave assistance. Their logical canvases, draw anchors and action cues remain
registered to existing rooms. The new registry contains 133 artwork exports.

`scene_contact_sheet.png` and the per-action GIFs show production `World.draw`
composition, furniture and native rendering. `scene_review.json` identifies the
scene, camera, logical size and retained native size for every sample.
`tools/capture_caelan_scene_actions_hd.py` stages those production poses with
temporary saves; these frames are visual review evidence, not a full scripted
rescue replay. The cup samples include the actual opening controller’s owned
cup overlay and release cue. The assistance samples check registration in the
cave; the rescue gameplay tests separately exercise the real actors and phases.

Review covered head/body scale, natural seated knees, stable support, two-limb
silhouettes, left-hip pouch continuity, rear prop occlusion and cup release.
The rear sack lift received a separate shallow forward-bend drawing after the
initial ground-reaching study proved unsuitable for a tall sack ahead of him.
The cup pass received its own reach/place/recover drawings after identifying
that the older intent studies depicted drinking rather than “Here, Mother.”

The old holding-torso/walking-leg splice, procedural Caelan arm builders,
blank arm layers and obsolete source bodies are removed. Retirement hashes and
all 141 unchanged approved travel PNG hashes are retained beside the new source
masters. Other actors and needed prop/FX inputs remain reproducible.

The separately authored opening and Ice Reaper cinematic banks have their own
larger masters, camera projections and action/costume requirements; they remain
active independent assets, as does combat art. `retained_cinematic_banks.png`
records representative inspected frames. This migration replaces the small
scene-specific overworld banks, not those distinct later cinematic performances.

Validation includes source/output hashes, deterministic rebuilds, native/detail
retention, source-bank retirement, actual pickup transfer, blocked approach,
opening action barriers/pause, household restoration, spell recovery, work prop
composition, cave rescue ownership and rendering regression checks. Four
save-validation failures in the household/lantern suites also reproduce on
unchanged main at `af4d24ee`; they are not suppressed in the repository tests.

Final validation: **209 tests passed in four isolated process batches** (69 asset,
travel/rendering/opening; 53 spell/mill/lantern; 46 rescue/interaction/participation;
41 household gameplay). The four separately confirmed baseline save-validation
failures were excluded only from the temporary batch runner, not changed or skipped
in repository tests. A combined process exceeded the environment memory limit;
batched runs completed. A final 19-test source/export/wake check also passed.
Both deterministic exporters pass `--check`; `git diff --check` is clean.
