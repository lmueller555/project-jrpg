# A Light of His Own — PR1 review

The capture uses the production Game, normal walking and door transitions, quest dialogue callbacks, companion staging and construction actions. Only completed MQ01–MQ03 prerequisites and the initial player station are seeded.

`quest.gif` is a time-compressed overview containing every main dialogue page. Use the native-resolution PNG stills and `dialogue.md` to read the script. `construction.gif` shows the real assembly and lifting actions.

The section ends at `frame_ready`: MQ04 remains active, its first two objectives are complete, and the lantern is unlit. The repaired mill remains running.

Reproduce with `python tools/capture_lantern_quest.py`.

Validation: all **568 tests** pass, including **23 MQ04 integration tests** and **11 actor-handoff tests**. The actual-game capture reads all nine main scenes and 170 dialogue pages, uses normal walking and school doors, and records 51 construction frames. Caelan’s grounded work/support poses preserve his approved idle head, legs and feet. Liam holds a single frame through the post-lift conversation and reload.
