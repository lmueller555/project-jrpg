# Mira Bolt Shot: firing-only review (PR1 of 2)

This change authors the mechanical release, not the flight/contact upgrade reserved for PR2. Original lift/aim pixels are preserved; the worn cuff compresses its latch/plates, snaps, recoils through the elbow and shoulder, settles, follows through slightly and lowers. The approved head and complete planted hip/leg chains are restored from the accepted aim snapshot. A tiny attached brass wedge replaces the former crossed glint. There is no explosion, smoke cloud or persistent vent effect.

## Production previews

- [Normal, with event-triggered clack audio](normal.mp4)
- [Reduced Motion, with event-triggered clack audio](reduced_motion.mp4)
- [Normal 25 fps GIF](normal.gif) and [4× slow](normal_slow.gif)
- [Reduced Motion 25 fps GIF](reduced_motion.gif) and [4× slow](reduced_motion_slow.gif)
- [Numbered native drawings](native_frames.png)
- [Normal production contact sheet](normal_sheet.png)
- [Reduced Motion production contact sheet](reduced_motion_sheet.png)
- [Boundary, pose, floor, HP, cue and mixer evidence](verification.json)

Both modes use the actual first MQ02 shot against Ridgeback Tusker, reached by the existing unseeded New Game input driver through MQ01 and MQ02. No party/enemy, ATB, damage, battle clock, camera, pose or effect is substituted. Save and settings paths are disposable. Music is muted to isolate effects; audio is reconstructed from the actual event-triggered cached buffers, not SDL loopback. Each MP4 has 101 frames at 100 fps, spanning the .80s action plus its ordinary following rest. GIFs are compact 25 fps references; PNGs preserve exact native colors. The production announcement may still show Caelan's preceding Aether Edge; that unrelated banner behavior is not changed here.

Both captures verify no projectile/damage at .279, release exactly at .280, one damage application at .400 and finish at .800. Mira's formation floor never moves. The dry clack fires once at .280 and decodes 11356 nonzero PCM bytes at the production 44100 Hz mixer (peak 2847 before cue gain). Reduced Motion omits the wedge but retains authored core poses, clack and the original projectile.

## Scope and validation

- Original first three aim PNGs and every unrelated Mira pose remain byte-identical.
- All 82 original spritesheet cells, including five now-unused firing poses, are preserved by hash and pixel checks; the eight new source drawings append to the sheet.85 complete drawings are actively referenced.
- Seven mill-combat asset tests pass, including source bounds, unclipped hard-alpha frames, original-sheet preservation and exact timing.
- Six firing-specific tests pass, including frozen release anchor, distinct authored mechanical phases, planted registration and audible clack at 44100/48000 Hz.
- Three action-audio tests pass for caching, mute, volume and channel cleanup.
- Full Mira regression suite: 91 tests pass serially.
- The broad repository suite was attempted and stopped after over 500 passing checks because unrelated failures were already present. Independent QA reproduced the doctrine text, Aqua/Bat save fixture and status-UI failures on unchanged main 16227da5. This is not a claim of a full-repository pass.
- Rebuilding the combat bank reproduces every output byte-for-byte.
- Independent review found no duplicated limbs, shoulder/neck/belt break or foot drift. The latch motion is deliberately subtle at native scale. The initial default-mixer audio defect found in QA is fixed with a scoped 44.1 kHz derived WAV, without changing global audio or other cues.

## PR2 handoff

The compatible `MiraCombatArt.shot(...)` result freezes `origin` from the exact snap drawing at .280s. Its native lens center is **[14,28]**, with floor **[32,54]**; at existing 2× battle scale the offset is **(-36,-52)**. `muzzle` follows the current recoiling cuff. Timing stays release .28, impact .40 and total .80. The current projectile/contact renderer is intentionally unchanged.

Reproduce with `python tools/build_mira_combat.py`, `python tools/build_mira_bolt_clack.py`, then `python tools/capture_mira_bolt_firing.py`. Source masters, prompt summaries, protected snapshots, hashes and the regional restoration recipe are retained in `assets/source/combat/mira_bolt_firing/`.

Keep this PR in draft until the coordinating independent review clears it. PR2 follows only after this firing-only change merges.
