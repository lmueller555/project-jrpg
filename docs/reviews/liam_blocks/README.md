# Liam's wooden-block play routine — awaiting review

- [Build all five blocks and put all five away](normal_cleanup.gif)
- [Build and tidy up, forgetting one block](forgotten_block.gif)
- [Daisy accidentally knocks the building over](daisy_accident.gif)
- [Close sequence: approach, contact, reaction and Daisy's return](daisy_accident_detail.gif)
- [Whole-room placement of the box between the beds](room_overview.png)

Captured from `main.py` using the actual room renderer, actor movement and
production block controller. The clips run at actual game speed, with a two-second
hold after completion. Only the initial long wait is skipped. The review chooses
the accident/forget decisions to show all outcomes; the game makes one 10% nearby
accident roll and one 50% cleanup roll per eligible session.

For the accident review, Daisy is given a normal nearby wandering destination
after the third block is placed. She walks from her rug; her position is never
snapped for the capture. Her proximity and availability still control whether
she can approach, and she touches the finished building before the blocks fall.

Five block identities persist throughout taking, carrying, placing, scattering
and tidying. The box loses a piece at the handoff frame and gains it back when
Liam puts that piece away. A forgotten block remains on the floor, with four
inside the box, and is collected at the start of the next session. The review
loop resets the preview scene; it does not add new blocks to the game.

Liam's overhead reaction does not pause player controls. Daisy walks to her rug
and settles after being told to lie down. Their outdoor chase routine cannot
start while Liam is building or tidying. The existing bed, rug and bowl assets
remain unchanged.

Reproduce with `python tools/build_liam_family_home.py`, then
`python tools/capture_liam_blocks.py`. `captures.json` records the actual state
sequence, selected outcomes, block states, positions and controller events.
This branch is published for review and has not been merged into main.
