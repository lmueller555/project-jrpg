# Caelan overworld quality review

This review samples the new runtime sprite bank through the real Player frame
selector and the production town/cave renderers. It also seeks representative
household interactions through their existing action owners. User approval of
the finished artwork is pending the requested preview.

- [Before/after standing directions](standing.png): four directional idles,
  enlarged six times, with a one-times native row. The old drawings are retained
  in the source archive; the updated row reads current runtime images.
- [Animated travel](travel.gif): idle, walking and running in all four directions.
  The animation seeks `Player.sprite()` on a 20 ms review clock over the shared
  2,800 ms cycle. Walk poses retain 140 ms, run poses 100 ms. PNG sprites remain
  authoritative; the GIF uses a shared 256-color review palette.
- [All 36 runtime drawings](native_contact_sheet.png): the individual four idles,
  sixteen walking poses and sixteen running poses at a constant enlargement.
- [Eldenmere](town.png) and [Sanctuary cave](cave.png): the production scene,
  lighting, foreground ordering and current Mira actor at staged clear floor
  positions. The lower inset is a four-times crop of the same lit native frame.
- [Scoped world pose samples](actions.png): breakfast, sitting, carrying,
  post-contact pickup and handover artwork from their actual runtime banks.
- [Production interactions](interactions.png): Halden pickup/contact/carrying,
  Venn supply transfer/recovery and gate tool work, and Elira lantern reach,
  acquisition, four-direction carrying, placement and release. Individual
  labelled stills are included beside it.

The Player still uses the existing 24×36 canvas, world draw registration and
movement/collision rules. Staged Mira comparison positions use her existing
registration; neither character is resized inside the world renderer.

These are isolated art/animation studies, not a played quest walkthrough or a
claim that every scene contact has been exhaustively validated. Household
prerequisites are seeded in separate disposable Games; their actual owners
then update the action clocks and transfers. SaveStore and recovery-save
publication are disabled in all fixtures. The travel fixture's quest/inventory
signature is checked unchanged. `evidence.json` records clocks, scene stations,
contact state and input/output fingerprints.

Halden retains the established standing preparation until the 0.36 s pickup
cue. This pass refreshes his carried/post-contact Caelan artwork. A new crouch
was examined in the real scene, where the unchanged source station left its
hand short of the sack; that staging remains a follow-up rather than a claimed
working reach animation in this review.

The final contact sheet was inspected for alternating front/back leading legs
and arm swings, consistent grounded registration across directions, readable
profiles, and the brighter town versus cave lighting. The interaction stills
were checked for Halden's front/rear sack layering, Venn's tool grip and release,
and Elira's lantern base support and shelf/table ownership boundaries. These
checks cover the pictured phases; broader scene staging remains outside this
sprite-quality pass.

Reproduce after building current exports:

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  python tools/capture_caelan_overworld.py
```
