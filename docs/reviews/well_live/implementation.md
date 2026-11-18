# Live well integration scope

PR4 connects the retained well/pail, independent mechanism and current gardener
to ordinary Eldenmere gameplay. The source of truth for its activation is
`well_runtime` in `assets/source/maps/eldenmere/town_hd/recipe.json`; the town
composer exports the same binding to the playable map and town manifest.

## Source and presentation

- Bind the retained 72×88 logical /144×176 artwork well at `[492,800]`.
  Keep its physical support `[504,840,48,48]`, collision, navigation, doors,
  garden targets and road clearances unchanged.
- Use `DrawingWell` as the live wrapper for one `WellMechanism`. Draw native
  back/front layers at logical sort baselines 840/896; keep all shaft and water
  occlusion inside the authored masks.
- Keep the existing `adult_woman_02` identity introduced after the PR3 art
  delivery. Its complete native action drawings supply eight registered body
  phases for the sixteen mechanical crank samples; normal unladen travel keeps
  the roster gait. Preserve the earlier bob-haired PR3 bank and approval records.
- Use the PR3 canonical pail variants for every visible pail state. Draw a held
  pail at its directional grip/depth, preserve its silhouette across fill levels,
  and start pour streams at its transformed target-facing lower mouth lip.

## Routine and timing

The existing rest/pickup/outbound/garden/return/setdown loop remains the owner of
the ambient gardener's work. At the well, the independent mechanism becomes the
sole functional clock. The actor samples its immutable snapshot for poses,
phase and ownership rather than maintaining duplicate well timers.

The operation passes through loading, attachment, operator approach, engage,
guide, lower, fill, raise, secure, retrieval approach and detachment. Loading is
`[528,894]`, facing back; operation is `[564,866]`, facing left. The safe route
between them goes through `[564,894]`. Readiness requires reaching and facing
the real station; collision or another actor can delay the approach without
advancing the mechanism. No path or contact repair stretches the body.

Attachment and detachment use the mechanism's once-only ownership cues. Water
fills only after geometric mouth submersion. Once retrieved, the same pail
travels to the six existing garden targets. Each pour consumes one unit at its
authored cue, then finishes its recovery without consuming again. Empty pails
produce no stream. Speeds remain 60/50 logical units per second for empty/loaded
travel; rest remains sampled once per cycle from the existing three–five minute
range. This ambient work grants no inventory items or quest rewards.

## Lifecycle

Pause, menus and focus loss freeze the exploration clock and operated mechanism
together. Ordinary indoor visits retain the same town actor, pail and mechanism,
so the cached offscreen town can continue its existing work simulation. Remote
world travel suspends town updates without applying elapsed-time catchup.

The ambient routine is transient rather than a new save subsystem. New Game and
Continue reset actor and mechanism together to the rest checkpoint, with one
deposited pail and no stale reservation/token. Existing save schemas and story
facts remain compatible. Coordinated cancellation/reset must never leave a
well-owned pail behind while starting another actor-owned copy.

## Acceptance

Review actual `Game` updates and native world draws for one complete physical
operation and the six-target garden loop. Verify clear probes and blocked gate
holds; once-only events and water consumption; body/pail/near-rim depth; stopped
crank phase; frame-rate consistency; pause/focus; interior continuity; New Game
and Continue restoration; and reduced-motion behavior. Drawing must remain
read-only, preloaded artwork must avoid repeated disk reads, and caches must be
bounded. Source/export checks remain separate from visual inspection.

The [live review](README.md) records the implemented checks, measured behavior,
captures and any remaining presentation limits. The centralized
[visual](../../VISUAL_ART_STANDARD.md), [terrain](../../TERRAIN_ART_STANDARD.md)
and [interaction](../../OBJECT_INTERACTION_STANDARD.md) standards retain their
authority; this document records only this integration's implementation facts.
