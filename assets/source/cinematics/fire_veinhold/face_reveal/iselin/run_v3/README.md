# Iselin frontal run continuity sources

This folder retains complete ImageGen-painted continuity repairs for the 48-drawing, 800 ms cinematic run. It preserves the blue/silver design, anatomical left braid and anatomical right mantle. The prior `run_v2` sources and the baseline profile are retained unchanged.

The isolated `candidate_source_art_48.json` and `selected_order.json` describe chronological order. Source filenames record authoring history and may differ from the effective frame index. In particular, the selected drawings around the late recovery were ordered by their visible knee and boot progression. No selected endpoint or source drawing is duplicated.

`generation_records.json` binds selected raw masters, exact prompts and input image hashes. `helper_generation_records.json` also retains rejected helper attempts and their archived references. `reference_snapshots` preserves the baseline exported images used as ImageGen references before production exports are replaced. Authoring overlays and material-only reference crops guide complete redraws; their pixels never enter production exports.

`helper_braid_generation_records.json` records the bounded braid subdivision. `authoring_history.json` distinguishes selected masters from rejected attempts. `build_provenance.py` verifies the retained selected-input hashes and writes the chronological selection record. The raw masters remain unchanged.

Each final source is a complete painted figure. The export recipe uniformly samples the whole drawing after measuring face density and neck position against the frozen appearance reference. It translates the entire drawing to the existing phase-specific neck position, retains the existing 1024×1024 canvas and [512, 960] anchor, and removes only alpha values of 16 or less before premultiplied-alpha Lanczos sampling. It does not stretch individual limbs, restore pasted regions, crossfade poses, warp hair or cloth, fit occupied silhouette height, or synthesize extra frames.

Run the isolated registration with:

```sh
python assets/source/cinematics/fire_veinhold/face_reveal/iselin/run_v3/register_candidates.py
```

It writes complete candidate exports under `/tmp/iselin_v3_candidates`. Promotion to the actor's active profile is a separate final selection step. The production exporter remains:

```sh
python tools/export_prologue_faces.py --actor iselin
```

Review uses chronological still strips, actual-pixel material contours, visible hand components and independently reviewed anatomical sole windows. Shape extrema are not claimed to be tracked material particles. Hidden heels and joints remain unmeasured. Static inspection and numerical checks do not establish that normal-speed playback was watched.

`manual_landmark_observations.json` records the observed circular waist buckle in frame 32. The automatic template had matched a chest clasp above the belt; `reviewed_belt_32_overlay.png` shows both locations. This hash-bound correction changes the measurement label only, with no change to the master, scale, neck registration or exported artwork.

`native_review` retains the final production-scale palette and braid pilot accepted by the root reviewer. Frames 13 and 14 use ImageGen color-only edits to remove a source-palette flash; the original successful pose drawings remain as geometry references. The motion audit retains scoped, source-hash-bound diagnostics for matte-edge percentile instability rather than changing its global motion limits.
