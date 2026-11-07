# Emerald grass in the game

![Production grass review](contact_sheet.png)

[Walking, running, standing and recovery](emerald_grass.mp4)

![Unpainted crops from the production screenshots](grass_detail.png)

The town and Sanctuary views use an ordinary disposable new exploration journey,
production Game movement and the normal town/overworld/Sanctuary contacts. Long
travel segments are omitted from the silent video. No quests, equipment or
character poses are seeded. Detail views are integer-enlarged crops of those
actual screenshots. The upstream still is explicitly an initialized production
World/Player fixture; it does not demonstrate the quest-gated transfer.

Grass parts during walking and running, remains parted while standing and
recovers after leaving. Every occupied review frame compares grass enabled and
disabled at the same real pose: opaque sprite pixels above row 25 remain identical,
while lower-body overlap is observed. The [verification record](verification.json)
retains counts, actual coordinates and final source/artifact fingerprints.

Regenerate with `python tools/capture_grass_rollout.py`; verify with
`python tools/capture_grass_rollout.py --check`. Captures use temporary save and
settings paths and do not modify journey files or map assets.
