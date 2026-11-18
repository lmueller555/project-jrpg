# Ridgeback Tusker: Bolt Shot recoil

Candidate for PR2 review. The original 16 drawings, general hurt animation
and defeat animation remain unchanged. This add-on is for one nonlethal,
unguarded hit in the production battle.

The built-in image editor was given enlarged, nearest-neighbor versions of the
existing idle and first generic hurt drawings as references. The edit brief was
three complete right-facing drawings: compress the struck near shoulder with
the head still at idle level; let the head follow slightly back and up while
the shoulder returns; ease both toward the idle. Keep the same proportions,
fur, tusks, four hoof positions and tail. Output a transparent strip without
weapon, scenery, effects or shadows.

- Retained complete master: `mq02_tusker_bolt_recoil.png`, SHA-256
  `e7085c230de90c7fb97f16e6aa2490a33ffcc00929fafb29c0a0a4d7e072ee85`.
- Protected registration reference: `assets/combat/ridgeback_tusker/idle_01.png`,
  SHA-256 `94c5dd88a95214c91128bbc992c86c80a6a496f62e2703fe1107fafcb664aca6`.
- Head elevation reference only: `assets/combat/ridgeback_tusker/hurt_01.png`,
  SHA-256 `99171c444a84cca8fc079ade71ee32ca1e24ddc22621ba334cabb06d6334633a`.

Run `python tools/build_tusker_bolt_recoil.py` to re-export just this addition
and its manifest record. The common crop density, nearest-neighbor
registration, binary alpha and edit windows are recorded in that exporter.
The registered canvas is 96×72, anchored at (48, 62). Pixel restoration
protects the tail, hindquarters, and hooves in all three drawings, and the
head in the initial shoulder-only key. It does not translate separate limbs
or animate a runtime rig. The sequence is a finite 55 ms shoulder key,
95 ms head recoil, 100 ms return and 70 ms idle settle, sampled from contact.

A second full edit covers the raised idle phase observed at contact in MQ02.
The brief was the same three-beat sequence, except the elevated snout and
head must stay elevated in the first key and the head follows slightly
further up in the second. The last key settles toward the raised idle, then
uses that exact idle drawing for the 70 ms rest. This bank is called
`bolt_hurt_raised` in the same manifest.

- Retained raised master: `mq02_tusker_bolt_recoil_raised.png`, SHA-256
  `6f98ebacc323af895c6a6b917a8f30635541d33c124305382efa2a3d8f4a7de5`.
- Protected raised registration reference:
  `assets/combat/ridgeback_tusker/idle_02.png`, SHA-256
  `50849274fc2a762a998adae29de57ab84c7413d7b998e9f9583d570b26defbc1`.
- All banks re-export together with the command above.

The other two low idle phases use the same complete low-head source crops,
retaining each starting drawing outside the corresponding repair window to
avoid a stance, head or tail jump on later shots. Their last frames are the
exact starting idles; there are no extra source cells.

- `bolt_hurt_low3` reference: `assets/combat/ridgeback_tusker/idle_03.png`,
  SHA-256 `e408eea0ce5d2004e740aa4205a3dc9db3fea3386c1ba07e418d96af93782119`.
- `bolt_hurt_low4` reference: `assets/combat/ridgeback_tusker/idle_04.png`,
  SHA-256 `3e568dfaad66d76c51c9f995f3b68007432a1d9f464c70b3ca4814455cabc87f`.
