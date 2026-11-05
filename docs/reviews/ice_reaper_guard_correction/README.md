# Ice Reaper: guard and sprite correction review

[Watch the updated twenty-second preview](preview.mp4) at 60 FPS, with the existing music and sound effects.

This revision makes two targeted corrections. Lucan dashes away from the camera, kneels between Rhea and the Ice Reaper facing his attacker, raises his shield over his face, and stays kneeling through the interception. His already-correct ending pose and facing are preserved. The Ice Reaper's final shot reuses her retained, previously approved sprite artwork.

The environment, panorama, camera trajectory, framing, perspective projection, shot timing, and other characters are preserved. Restoring the Ice Reaper's art does not restore the older camera or screen-sliding foreground effect.

Review:

- [Dash, kneel, raise, and impact filmstrip](rescue_filmstrip.png)
- [Guard before and after](guard_comparison.png)
- [Impact before and after](impact_comparison.png)
- [Final shot: sprite-only before and after](final_shot_comparison.png)
- [Final shot filmstrip](panorama_filmstrip.png)
- [Retained approved Ice Reaper source sprites](approved_reaper_art.png)
- [Preservation checks](correction_scope_verification.json)
- [Production capture verification](verification.json)

The saved PR108 baseline is retained in [scope_baseline.json](scope_baseline.json). It checks 899 camera samples, ten direct-render background hashes, the unchanged camera/environment/projection methods, and seven late Lucan heading/position/frame hashes. These direct runtime checks are separate from the lossy MP4 comparisons.

The preview audio is reconstructed from the runtime score and identical timed sound files and gains because SDL dummy has no hardware loopback. Historical review assets remain in `docs/reviews/ice_reaper_continuity`.

Replay from Title → Gallery → Scene Studies → Ice Reaper: Frozen Clearing (20s). P pauses, R restarts, and Esc returns to Gallery. The scene cannot advance or overwrite the saved journey.

Validation: all **130 focused tests passed** across Ice Reaper stage, facing, blocking, environment, audio, playback and requested-correction checks, Gallery session/catalogue, and the original opening cinematic. The production video contains exactly 1,200 frames at 60 FPS and twenty seconds of audio; saves/settings are unchanged. Three opening reference images remain pixel-identical. All 899 camera samples, ten background hashes, six protected method hashes, and seven late Lucan pose/heading/position samples match the pre-correction baseline.

This revision is awaiting user review and remains unmerged.
