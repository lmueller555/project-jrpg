# Positional audio review

[Actual-game MP4 with audio](regional_audio.mp4) (116.8 seconds).
[Capture telemetry](capture_report.json) records accepted starts/stops, markers,
listener positions and representative voice gains.

The video is production `Game.update` / `Game.draw`, at 30 simulation updates
and 15 video frames per second, normal regional zoom. The fixture seeds prior
quests and the repaired mill, positions Caelan at the farm and bridge, advances
dialogue pages, and walks a clear east riverbank. Later world transfers and the
stress fixture are explicit capture setup, not new in-game interactions.

| Time | Review beat |
| --- | --- |
| 0–17.6 | Farm rustles, finite sack placements and stationary lashings |
| 17.6–79.4 | Bridge sorting, tool contact, full tea scene and cup return |
| 79.4–84.8 | River approach: zero, mid, then full .55 base gain |
| 84.8–90.8 | Walk away beyond hard cutoff; voice released |
| 90.8–96.8 | Return to audible range |
| 96.8–98.8 | Effects mute: exactly zero PCM |
| 98.8–100.8 | Unmute: nearby river returns |
| 100.8–102.8 | Map pause: exactly zero PCM |
| 102.8–104.8 | Resume |
| 104.8–106.8 | Town transfer: exactly zero PCM |
| 106.8–108.8 | Region return |
| 108.8–110.8 | Labelled stress fixture: two beds and six candidate cues; four-voice cap |
| 110.8–114.8 | Wind from an authored grain field |
| 114.8–116.8 | Title: exactly zero PCM |

The stress fixture uses deliberately colocated extra families to exercise the
shared scheduler. Those sources are not added to authored world content. Music
is disabled for review. There is no decorative soundtrack.

## Audio capture and evidence limits

SDL's dummy device cannot supply a hardware loopback. The capture therefore
renders the production controller's accepted start/gain/stop stream offline
using exactly the same PCM synthesis and gain multipliers, at 48kHz mono. Mock
channel leases replace only the SDL output device. Production game-time cue
expiry drives the recording, so simulation speed cannot alter clip duration.
The recorder performs no normalization, limiting, soundtrack substitution or
post-hoc event additions. FFmpeg encodes the resulting audio as AAC in the MP4.

The PCM peak is -13.29 dBFS; there are no clipped samples. Mute, pause, town and
title intervals were checked sample-by-sample for exact zero before AAC encoding.
AAC can have codec ringing at boundaries; the production mixer and source PCM
cutoff are exact. Synthesis tests check distinct waveforms and safe peaks.
Visual frames were inspected for the farm, tea handoff and river route. Contact
telemetry shows the two sack placements at 5.57/12.37s and cup contacts at
55.67/56.83/77.37s. Independent code review found and resolved the false tender
stone cue, ambient seam and first-frame cue ageing issues.

**Listening review remains pending:** this execution environment provides no
verified perceptual audio-input/audition facility. The MP4 contains the actual
regional mix, but waveform evidence does not establish that each synthesized
material sounds convincing. Keep the PR draft until a human or audio-capable
reviewer listens to the final MP4 and accepts material identity, level and timing.
No audio approval is claimed.

Reproduce with `python tools/capture_regional_audio.py` (pygame, numpy, Pillow and
FFmpeg). The intermediate WAV is generated locally and omitted from git to
avoid duplicating the soundtrack. All audio is original synthesis; see
[architecture/provenance](../../REGIONAL_AUDIO.md).
