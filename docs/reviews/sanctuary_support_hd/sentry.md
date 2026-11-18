# Sanctuary lookout native identity

Only the arrival scene's brown-haired, green-dressed lookout (`sentry`) moves to the corresponding approved `adult_woman_02` design and matching portrait. Eight manifest-timed frames in each facing, 560 ms full cycle; 48x72 native artwork, 24x36 world, unchanged [12,30] draw anchor and navigation/collision.

The lookout has no object or special activity clips. No other arrival support actor, caretaker unhook, injured pose, attendant carry pose, playable character, or reserve gardener is migrated by this change. In particular, the reserve's `reserve_caretaker` is not the arrival `caretaker`.

The generic fallback is overridden through CastActor's existing density-aware art path. Actor-defined portrait paths now work for the three secondary support roles without altering shared female_02 portrait registry entries. Exact eight-frame playback and preserved registration covered by `test_sanctuary_sentry_native`.
