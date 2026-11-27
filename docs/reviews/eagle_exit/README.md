# Eagle exit after the crest

After cresting at 15s, the eagle descends through the lower edge at full sprite
scale. It has fully cleared the frame by 17s, leaving the rest of the ten-second
vista unobstructed. The camera continues a restrained forward push through 25s
instead of following the eagle down. There is no bird fade or shrink-away.

- [Updated production preview](shot01.mp4)
- [Reduced Motion preview](shot01_reduced_motion.mp4)
- [Exit frames at 15/15.5/16/16.5/17/20s](exit_filmstrip.png)
- [Unobstructed fortress at 20s](shot01_600.png)
- [Actual Gallery replay](gallery_replay.png)

The completed shot remains 25 seconds, with the same fortress, smoke, beacons,
wind and Gallery fixtures. Both individual and complete Gallery entries use
this production controller. Existing source artwork is unchanged.

**27 targeted tests passed**: controller timing/rendering/lifecycle, eagle exit
continuity and complete offscreen bounds, continued camera movement after the
exit, save/settings isolation and both Gallery entries' production completion.
See [test output](tests.log). Compilation, whitespace and capture-hash checks
pass. The 20 unrelated Gallery thumbnails/records remain unchanged.

Normal and Reduced Motion movies each capture 750 actual production Game.draw
frames at 30 Hz in a 960×640 Gallery viewport. Capture JSON records current art
and runtime hashes. Audio remains the existing offline production cue mix.
Earlier review folders retain historical versions.

```sh
PYTHONPATH=.:tests SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m unittest \
  tests.test_fire_veinhold_opening \
  tests.test_gallery_catalogue.GalleryCatalogueTests.test_fire_veinhold_opening_production_completion \
  tests.test_gallery_catalogue.GalleryCatalogueTests.test_fire_veinhold_shot_01_production_completion \
  tests.test_gallery_catalogue.GalleryCatalogueTests.test_fire_veinhold_lists_complete_replay_and_only_completed_shots -v
python tools/capture_fire_veinhold_opening.py
python tools/capture_fire_veinhold_opening.py --reduced-motion
python tools/capture_gallery.py --mode thumbnails \
  --scene fire_veinhold_opening --scene fire_veinhold_shot_01 \
  --out docs/reviews/eagle_exit/gallery
```
