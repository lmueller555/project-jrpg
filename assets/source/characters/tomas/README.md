# Tomas — retained front-idle source

`idle_front_concept.png` retains the generated transparent appearance concept, informed by the approved Caelan art for style and the agreed Tomas design: younger foster brother, blond cowlick, green eyes, short rust-red tunic, ivory sleeves, dark trousers, repaired left knee and ankle boots. This adds no new story facts about his precise age or history.

`export.json` records alpha threshold, source bounds, nearest-neighbor source bands, named garment windows, two eye landmarks and layer rows. Source bands register a 32-pixel visible character inside the shared 24×36 frame: head starts at row 3 and feet end at row 34. Garment windows preserve pale sleeves, rust fabric and the single knee patch; pupil/iris landmarks keep both eyes distinct after reduction. The retained source is a concept, while the native PNG is the game asset under review.

Run `python tools/build_tomas_idle.py`. It writes four full-frame RGBA layers (`head`, `upper_body`, `tunic_hem_and_hands`, `legs_and_boots`) that reconstruct the idle exactly, native metadata/palette references and two opaque enlarged review images. Existing approved cast sprites, templates, environment assets and narrative files are read only. No walking poses or other directions are introduced.
