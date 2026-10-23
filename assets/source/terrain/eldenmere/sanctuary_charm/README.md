# Sanctuary charm source

New art is retained in `props_concept.png`: a two-seat bench, herb box,
provision basket, corner vine and worn flagstones. The original generated
reference is preserved; `recipe.json` records each crop, native size, palette
classification and placement. `parts/` contains the resulting native samples.

Run `PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/project-jrpg/bin/python tools/build_eldenmere_sanctuary_charm.py`
from the repository root. Pillow is the only external dependency. All prior
sanctuary, cottage, town, foliage and character inputs are read-only.

The 24px terrain scale and 24×36 Caelan sprite are unchanged. Bench and basket
have local planning footprints. Herbs are mounted below the two left windows;
the vine sits against the west corner. Existing approved foliage and flowers
supply the garden edges. No cloth ties or birds are added.

Animation is confined to sampled leaf pixels, the hanging lantern body, smoke
and an optional bell cue. Container and stem pixels, roots, trunks, shadows and
the lantern bracket stay fixed. The 5.4-second eastward foliage cycle and
3.6-second smoke/lantern cycle repeat together after 10.8 seconds. The ambient
bell is still; its separate nine-pose cue is authored for a single playback.
The lit lantern insert is a separate art variant, not a time-of-day system.

Status remains `review` until the user approves this charm pass. The previously
liked sanctuary exterior is reused without modifying its source or exports.
