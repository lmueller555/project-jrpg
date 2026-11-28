# Overhead phases32–47

`master.png` is the unchanged ImageGen source master. Its exact prompt and three
input reference hashes are in `generation.json`. The first input is the
annotated3D pose guide from the sibling helper; the other inputs are head/hair
and blue/silver coat material crops. No guide pixels are final character art.

This source starts with a bent-knee, folded-calf passing silhouette and advances
the anatomical right/image-left foot toward the next right contact. Complete
figures were drawn together; no limb cutouts, image warps or pose blends are
used. Native phase continuity, model/cloth joins and the loop seam remain the
parent exporter's acceptance gates.

The generator returned1247×1261 instead of the guide sheet's1024×1536. Whole
drawings retain their actual aspect and proportions. `observed_source_cells.json`
records the actual empty row gutters:0,290,620,940,1261. Equal quarter cuts would
include a few hair-tip pixels from the following row. The observed crop edges
all contain zero alpha>16pixels; whole-figure cropping resolves that packing
issue without changing artwork pixels or fitting silhouette heights.

`selection.json` binds every candidate phase to the raw source hash and observed
whole-figure crop. `alpha_corner_audit.json` retains the diagnostic nominal-grid
corner measurements; the observed source-cell audit supersedes those nominal
row edges. Production registration and the portable actor profile are owned by
the parent exporter, and were not changed here.
