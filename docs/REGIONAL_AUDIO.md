# Regional positional audio

`RegionalAudio` owns at most four leased mixer channels: two ambient beds and
two incidental cues. Each class allows one voice per family. Higher priority
wins, then higher current distance-adjusted gain; an existing equal voice wins
the tie. Ambient candidates are sorted deterministically. If SDL has no free
channel, the cue is dropped rather than stealing another controller's channel.
No music calls, channel reservations, or mixer resizing occur.

The listener is `game.player.position` in global pixels. Camera focus, atlas pan,
and minimap framing never enter the gain calculation. A source has base gain,
near radius, far radius, priority, family and optional live position callback.
Between near and far the multiplier is `1 - smoothstep(t)`. At or beyond far,
the multiplier is exactly zero and the owned channel is stopped/released.
Ambient activation requires entering 12 pixels inside far; an already active
bed continues to the exact hard boundary. This prevents boundary chatter.

| Sound | Base gain | Near/far (pixels) | Family / priority |
| --- | --- | --- | --- |
| River | .55 | 36 / 260 | water / 1 |
| Crop/woodland wind | .45 | 24 / 150 | foliage / 0 |
| Sack, cloth, parked lashing | .5 | 32 / 180 | farm / 2 |
| Tool on stone | .5 | 32 / 180 | masonry / 2 |
| Cup contacts | .5 | 32 / 180 | ceramic / 3 |

A single river source follows the nearest point on the nearest authored river
edge. A single wind source follows the nearest authored woodland, grain or
orchard polygon (zero distance while inside). Neither feature creates tile
emitters, allocates chunks, or changes cache bounds. Voices retain current
source positions, including actor callbacks, while playing. No rolling-cart
sound is used for the stationary farm cart.

Farm cloth cues occur at lift/cover beats, sack impacts at finite placements,
and creaks at the lashing gesture. The optional sack exchange has a lowering
contact. Bridge ceramic contacts match the unstable stone, safe tray, and final
return. Stone strikes follow the tool owner's lowered animation frame; cup
handling at the kettle cannot emit tool strikes. The tool prop follows that
one-pixel hand motion. Incidental cooldown is .6 seconds per event key; there
is no event queue. Distant, muted, paused, unavailable-device and budget-rejected
cues are discarded immediately. Quiet work has no fabricated cargo impacts.

Effects settings notify the controller immediately, including while a menu is
open. Regional menus, focus loss, combat, title, town/interior transfer and
opening/RegentArrival scenes release regional voices. Resuming starts eligible
beds afresh and never resumes old impacts. Continue resets leases and cooldowns;
no audio fields or handles enter saves. Existing durable work checkpoints
prevent completed placements and tea interactions from replaying.

Channels are touched only while `channel.get_sound() is owned_sound`. A reused
channel is forgotten without changing its gain or stopping its new owner.
Missing devices, unsupported sample formats and mixer failures disable playback
without affecting work controllers. Sounds are generated only for the current
signed-16-bit mixer format and cached per format; failed playback can retry after
a journey reset. This PR provides attenuation, not stereo pan or obstruction.

All seven sounds are original deterministic synthesis in `regional_audio.py`:
filtered noise and low resonance for cloth/sacks, nonharmonic damped partials
for stone and ceramic, irregular wood resonance for lashings, and filtered
cyclic noise for water/foliage. No external recordings, licenses, or paid assets.
The PCM and mix leave substantial headroom. Future sources should use new
families only when they warrant sharing the two incidental slots, retain actual
physical event hooks, and never enqueue inaudible actions.

Run `python -m unittest discover -s tests -v`. Focused coverage lives in
`test_regional_audio.py` and `test_regional_audio_events.py`; the existing farm,
bridge, world, save, arrival and audio-setting tests remain regression coverage.
See [audible review](reviews/regional_audio/README.md) for capture details.
