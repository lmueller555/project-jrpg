# Gallery review

This original Gallery review covers 25 immediately available production scene previews.
The wildlife pass adds **A Familiar Visitor** as entry 26, with its own
production thumbnail and completion/restart/save-isolation tests. Its finite
sheep visit and evidence are documented in the [wildlife review](../purposeful_wildlife/README.md).
The screenshots and video below retain their original 25-entry capture;
the thumbnail contact sheet includes the new entry.
Each card has a captured thumbnail, a name, chapter and description. The full
[coverage matrix and extension guide](../../GALLERY.md) documents fixtures,
boundaries and intentional exclusions.

## In-game evidence

- [Replay video](gallery_review.mp4): title → keyboard Gallery navigation →
  mouse wheel scrolling → prologue/Skip → Aldric arrival/Escape → mill repair
  completion → lantern finishing completion → retained selection → title →
  Continue of the original saved journey.
- [Gallery top](gallery_top.png), [scrolling](gallery_middle.png),
  [last entries](gallery_bottom.png), and [retained selection](gallery_return_selection.png).
- [All 26 actual thumbnails](thumbnail_contact_sheet.jpg).
- [960×640 catalogue](gallery_960x640_text1.png),
  [480×320 at 150% text](gallery_480x320_text1.5.png),
  [800×800 at 150% text](gallery_800x800_text1.5.png), and
  [1920×810 catalogue](gallery_1920x810_text1.png).
- Production dialogue remains clear of the separate replay toolbar:
  [Aldric at 960×640](arrival_dialogue_960x640.png),
  [Aldric at 480×320/150%](arrival_dialogue_480x320_text1.5.png),
  [millrace at 960×640](millrace_dialogue_960x640.png),
  [millrace at 480×320/150%](millrace_dialogue_480x320_text1.5.png).
- [Regional bridge tea](regional_bridge_tea.png) and
  [garden quiet care](regional_garden_quiet_care.png), plus
  [Continue of the original save](continue_original_save.png).
- [Finite sheep and basket visit](regional_sheep_basket_visit.png): the new
  automatic replay at its production pat contact, shown with the Gallery toolbar
  and normal regional zoom. The complete visit runs about 62 seconds through
  basket return and release of the original gardener.

## Reproduce

Install the normal game dependency plus Pillow, with ffmpeg on PATH, then run:

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python tools/capture_gallery.py --mode all
```

`--mode thumbnails` refreshes the 320×180 production-canvas crops;
`--mode review` refreshes the video and screenshots. No normal save directory is
used. [Capture metadata](capture.json) records the source commit, runtime source
hash, events and replay-return save-byte checks. The
[thumbnail provenance](../../../assets/ui/gallery/capture.json) records each
source frame, controller phase, crop and PNG SHA-256.
`--mode thumbnails --scene sheep_basket_visit` captures only the new thumbnail
and full replay still, preserving the original 25 thumbnails and their global
provenance. The new record supplies its own source commit and runtime hash.

Animation/camera time runs at the normal 30 Hz. Automated dialogue acknowledgement
is brisk (0.4–1.0 seconds between inputs) to keep the review concise. The video is
**silent**: SDL dummy offers no audio loopback, so it is visual/input evidence and
does not claim perceptual listening. Audio ownership and effects cleanup are
verified separately by runtime tests, including real dummy-mixer regional voices
and an unrelated sound that must survive preview cleanup.

## Regression scope

`test_gallery_catalogue` discovers a completion test for every registered scene,
including the full unskipped 252.57-second opener. It checks controller boundaries,
collision-valid starts/ends, unique actors and disabled saving. `test_gallery_session`
exercises every scene with actual rendered dialogue and production input, plus
current/legacy/missing/invalid saves, save/settings byte immutability, repeated
launch/restart/return, Continue, incidental encounter suppression, focus handling,
window changes, sound ownership and missing lazy-asset recovery. `test_gallery_ui`
covers empty/long catalogues, missing thumbnails, lazy image caching, keyboard
focus visibility, wheel clamping and varied display/text sizes.

The PR records the full regression suite's exact tested commit and discovered/
passed count. Modules run in fresh processes with at most three workers, so
Pygame asset graphs from unrelated suites do not accumulate in one process.

Normal exploration retains integer pixel scaling. A replay fits its complete
scene below the toolbar with nearest-neighbor scaling and display-resolution
text. Gallery scenes are bounded previews; ordinary errands, battles, free travel
and repeating NPC routines are intentionally outside the catalogue.
