# Cave Bat combat review

These captures render the canonical Cave Bat at levels 2 and 3 through the production `BattleModel.from_bestiary` and `BattleScene`. The contact sheet shows both ready states, Bite contact and Wing Gust impact. The full images retain the game's 960 × 640 display resolution.

The existing **Eldenmere battlefield is a review stage**. Cave Bat reuses the existing Bat drawings. These images do not introduce cave scenery, new monster artwork, world encounters or a cave unlock.

The capture tool creates a real `Game` with temporary journey and settings paths. Caelan receives approved growth stats for the matching level through a copied character catalog; the encounter uses RNG seed 7 and ordinary ATB. Real mouse commands select Guard until the enemy has acted eight times, then Attack through victory. HP, MP, damage, animation clocks and poses are not replaced. Audio is muted for headless capture.

The level 3 event record proves the sequence Bite, Wing Gust, Bite, Wing Gust, then free Bite fallback: enemy MP falls **5 → 3 → 1**, with exactly two Gusts. The rendering check covers actual Bat idle, attack, cast, hurt and defeat frames while gameplay events retain the `cave_bat_bite` and `cave_bat_wing_gust` IDs. Source attributes remain unchanged after the isolated encounter.

XP values are encounter metadata; this review does not award XP. Loot is undecided. Cave Bat's authored elemental profile is Non-Elemental, with 200% Fire damage received, 100% for every other type and no absorption. Its fragile wing membranes provide the Fire-weakness clue. Elemental combat effects, low Stagger resistance, spawn placement, progression rewards and Edran's planned Study reveal remain future work. Ordinary combat does not reveal this internal profile.

Regenerate and verify from the repository root:

```sh
python tools/capture_cave_bat.py
python tools/capture_cave_bat.py --check
python -m pytest -q tests/test_bestiary_scene.py
```

`verification.json` stores the actual action/impact events, capture resources and SHA-256 fingerprints of the production logic, canonical data and rendered assets. `--check` rejects changed sources or image artifacts so stale pictures cannot pass as current evidence.

Validation on the captured sources: **3 tests and 2 level subtests passed**; capture generation and an independent `--check` both passed. The presentation test compares text and pixels for the canonical profile against a different valid element/affinity profile and confirms that neither is revealed by the battle UI. A deliberately changed source fingerprint was rejected during initial capture-tool validation. The contact sheet was visually inspected for names, action poses, impacts and ready-state layout; regenerating after the elemental data update produced identical image files.

The initial Bestiary integration passed **494 tests and 3,111 subtests**: 442 tests / 2,761 subtests across the Bestiary, enemy growth, leveling, battle models and presentation, party gameplay, saves, Spoils and MQ02 encounter suites; plus 52 tests / 350 subtests covering progression cleanup, retired-save migration and character attributes/caps. Both runs used dummy SDL video/audio drivers. Independent checks also verified exact equality of the migrated Bat and Tusker records against the preceding main revision, unchanged legacy action potencies, every Cave Bat level-2/3 stat and XP value, resolved documentation links, and a clean `git diff --check`.

The elemental authoring update passed **229 tests and 1,717 subtests** across 20 Bestiary, combat, UI, enemy-growth, party, save/migration, reward and MQ02 suites. A final preview-only check passed **6 tests and 7 subtests**, including precise display of fractional percentages and absorption precedence. Independent review confirmed all nine identities, full relationship tables, arbitrary finite 0–200% values, strict absorption declarations, detached metadata and rejection of malformed profiles. Fixed enemy records and Cave Bat's level-2/3 growth, actions, resources and XP remain equal to the preceding main revision. Regenerated captures and their source/artifact fingerprints pass `--check`.
