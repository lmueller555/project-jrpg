# A Lantern of His Own — review

The capture uses the production Game, normal walking, real sanctuary, home and school doors, all twelve final dialogue callbacks, and all material actions. Only the shipped PR3 endpoint and earlier quests are seeded.

`quest.gif` includes every main dialogue page in a time-compressed overview under 1 MB. `motion.gif` shows real material work and covered-lantern carrying. Native PNG stills and `dialogue.md` provide readable dialogue; `pose_board.png` shows the sprite poses at pixel scale.

At `done`, all eight MQ04 objectives are complete. The single finished lantern is stored unlit at home, Mother is still teaching at school, and the afternoon and prior village repairs persist. The festival has not started.

Reproduce with `python tools/capture_lantern_finish.py`.

The uninterrupted four-part verification starts from MQ04 available, never seeds intermediate MQ04 progress, and completes all 43 scenes, 817 main dialogue pages and eight objectives through 15 actual doors. See `full_quest_verification.json`; reproduce with `python tools/verify_lantern_full_quest.py`.
