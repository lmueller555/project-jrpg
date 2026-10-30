# The Regent's Road — interior staging and following review

The production Game is played from MQ03 availability to completion. Only completed MQ01/MQ02 prerequisites and the initial player station are seeded. All six main conversations, the cart release, player walking, NPC following and door transfers use the normal quest controllers. Temporary saves leave ordinary journeys untouched.

- [Complete quest overview](quest.gif) — travel is compressed; every main dialogue page remains.
- [Cart release](cart_release.gif) — Mr. Venn and his cart visibly depart.
- [Actual NPC following](following.gif) — movement is sampled at ten frames per second.
- [Preparations inside the dining room](preparations.png)
- [Welcome and meal](welcome.png)
- [Aldric and Serene's discussion](discussion.png)
- [Private aftermath](aftermath.png)

- [MQ04 invitation in the same dining room](lantern_handoff.png)

The player walks from the dining room through the hall and courtyard to meet the visitors, then leads them back through the same doors. All local conversations and the visitors' final stations are inside the sanctuary dining room. MQ04 becomes available normally; its invitation is then read with both Tomas and Serene present inside. The road dispute and unresolved excavation decision are preserved.

`capture.json` records room transitions, dialogue locations and actual facing-change timestamps. Sustained follower turns respect the shared minimum turn interval; brief pauses remain in the measurement; scripted poses, dialogue, prolonged idle and room transfers are separate. The following clip uses ordinary collision-aware pathfinding, not direct actor movement.

Reproduce with `python tools/capture_regent_quest.py`.
