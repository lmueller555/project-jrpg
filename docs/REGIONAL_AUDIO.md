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
| Sack, cloth, parked lashing | .5 | 32 / 180 | farm / 2 |
| Tool on stone | .5 | 32 / 180 | masonry / 2 |
| Cup contacts | .5 | 32 / 180 | ceramic / 3 |

A single river source follows the nearest point on the nearest authored river
edge. Forests, grain fields and orchards do not emit ambient wind. River
placement does not create tile emitters, allocate chunks, or change cache bounds.
Voices retain current
source positions, including actor callbacks, while playing. No rolling-cart
sound is used for the stationary farm cart.

Farm pickup cloth cues occur at completed grabs, cover cues at their work beats,
sack impacts at completed placements,
and creaks at the lashing gesture. The optional sack exchange has a lowering
contact. Bridge ceramic contacts match the unstable stone, safe tray, and final
return. Cup placement contacts occur after the full set-down animation, together
with the ownership/location snap. Stone strikes follow the tool owner's lowered animation frame; cup
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

Sounds are original deterministic synthesis in `regional_audio.py`:
filtered noise and low resonance for cloth/sacks, nonharmonic damped partials
for stone and ceramic, irregular wood resonance for lashings, and filtered
cyclic noise for rivers. No external recordings, licenses, or paid assets.
The PCM and mix leave substantial headroom. Future sources should use new
families only when they warrant sharing the two incidental slots, retain actual
physical event hooks, and never enqueue inaudible actions.

Run `python -m unittest discover -s tests -v`. Focused coverage lives in
`test_regional_audio.py` and `test_regional_audio_events.py`; the existing farm,
bridge, world, save, arrival and audio-setting tests remain regression coverage.
See [audible review](reviews/regional_audio/README.md) for historical capture
details; that recording predates the removal of wind audio.

Regional garden/orchard work uses two finite synthesized materials: leaf handling and
soft fruit/wicker contact. Its filling-can and watering actions are silent;
their animations, timings and saved action progress are unchanged.
The remaining sound producers live in
`garden_orchard.py`, share the `garden_work` incidental family, and emit only at
physical beats. Pickup and placement contacts occur when their animations
finish and the object snaps to its new owner or resting place. Other work
contacts keep their authored timing. Contact time persists with the worker action, preventing a
Continue from repeating an already-heard contact. Existing attenuation, hard
cutoff, pause/exit handling and four-voice budgeting are unchanged.

## Eldenmere well feedback

`WellAudio` shares the identity-checked channel leasing engine, with its own
town-only eligibility, original synthesized material bank and attenuation curve.
It uses the existing Effects volume and leaves the regional sources and music
mix unchanged. The well and its gardener retain ownership of the work clock,
water and transfers; audio only observes their snapshots and event IDs.

Well work is centered at logical world `[528,864]`. Its multiplier is full through
32 logical units, then falls as `((80-distance)/48)^3`; it is exactly zero at or
beyond 80 units. Relative levels are approximately 29.6% at 48 units, 3.7% at 64,
and 0.46% at 72. These percentages multiply each material's restrained base gain
and the user's Effects setting. Camera position does not affect hearing.
The existing ambient activation inset prevents repeated starts around the edge;
active sounds still stop at the exact 80-unit boundary.

The winding/rope bed follows actual crank movement, and the small filling bed
requires the submerged-mouth fill phase. Hook contacts, water entry and emergence
drips use the mechanism's once-only event IDs. The gardener's finite pouring cue
starts at visible flow and follows the pail, using the same short 32/80-unit bubble
at its actual garden location. It cannot be heard back at the well from the distant
Sanctuary beds. Pickup/resting poses and completed empty pours emit no fabricated
water sounds.

Pause, focus loss, modal menus, examination dialogue, combat, title and scene exit
release owned voices. Ordinary indoor visits can continue the ambient chore, but
its inaudible contacts are consumed immediately. Muted, distant, interrupted and
budget-rejected cues are never queued. A contact more than 125 ms old is discarded
after a long frame; the current winding/fill bed may restart when eligible, while
old impacts and mid-flow pours do not replay on return or unmute. New Game,
Continue and ambient reset clear audio leases and observation history without
serializing handles or granting gameplay progress.

The material PCM is deterministic and generated for the available signed-16-bit
mixer format. Game construction prepares the six sounds without playing them or
leasing a channel, keeping the first nearby operation from doing cold synthesis
during movement. Missing devices, unsupported formats or playback failure remain
nonfatal. Focused coverage is in `test_well_audio.py`,
`test_well_examination.py` and `test_well_feedback_gameplay.py`; the
[well feedback review](reviews/well_feedback/README.md) records the accepted-voice
stream, cutoff measurements and reproducible review procedure.
